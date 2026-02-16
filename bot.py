#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3
from datetime import datetime
from urllib.parse import urlparse
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

TOKEN = "8470535043:AAEafK7ExK2vxMX7w_NbcMQeVuZppzLmUbI"
DB_PATH = "ex_amigos_repo.db"

MIEMBROS = {'German': '📚', 'Leo': '🎬', 'Mario': '🎵'}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER, chat_title TEXT, user_id INTEGER, username TEXT,
            content_type TEXT, source TEXT, url TEXT, file_id TEXT,
            caption TEXT, tags TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def classify_url(url):
    domain = urlparse(url).netloc.lower()
    sources = {
        'youtube.com': 'YouTube', 'youtu.be': 'YouTube', 'instagram.com': 'Instagram',
        'twitter.com': 'Twitter', 'x.com': 'Twitter', 'facebook.com': 'Facebook',
        'tiktok.com': 'TikTok', 'spotify.com': 'Spotify', 'vimeo.com': 'Vimeo'
    }
    for key, value in sources.items():
        if key in domain:
            return value
    return 'Web'

def extract_tags(text):
    return re.findall(r'#(\w+)', text) if text else []

def save_content(chat_id, chat_title, user_id, username, content_type, source, url=None, file_id=None, caption=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    tags = extract_tags(caption)
    tags_str = ','.join(tags) if tags else ''
    cursor.execute('''INSERT INTO content (chat_id, chat_title, user_id, username, content_type, source, url, file_id, caption, tags)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (chat_id, chat_title, user_id, username, content_type, source, url, file_id, caption, tags_str))
    conn.commit()
    content_id = cursor.lastrowid
    conn.close()
    return content_id, tags

def get_statistics(chat_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM content WHERE chat_id = ?', (chat_id,))
    total = cursor.fetchone()[0]
    cursor.execute('SELECT content_type, COUNT(*) FROM content WHERE chat_id = ? GROUP BY content_type', (chat_id,))
    by_type = cursor.fetchall()
    cursor.execute('SELECT source, COUNT(*) FROM content WHERE chat_id = ? GROUP BY source ORDER BY COUNT(*) DESC LIMIT 5', (chat_id,))
    by_source = cursor.fetchall()
    cursor.execute('SELECT username, COUNT(*) FROM content WHERE chat_id = ? GROUP BY username ORDER BY COUNT(*) DESC', (chat_id,))
    by_user = cursor.fetchall()
    conn.close()
    return {'total': total, 'by_type': by_type, 'by_source': by_source, 'by_user': by_user}

def search_content(chat_id, query_type=None, query_value=None, limit=15):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if query_type == 'type':
        cursor.execute('SELECT * FROM content WHERE chat_id = ? AND content_type = ? ORDER BY timestamp DESC LIMIT ?',
                      (chat_id, query_value, limit))
    elif query_type == 'user':
        cursor.execute('SELECT * FROM content WHERE chat_id = ? AND username = ? ORDER BY timestamp DESC LIMIT ?',
                      (chat_id, query_value, limit))
    else:
        cursor.execute('SELECT * FROM content WHERE chat_id = ? ORDER BY timestamp DESC LIMIT ?', (chat_id, limit))
    results = cursor.fetchall()
    conn.close()
    return results

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Bot Clasificador - Ex-amigos\n\nOrganizo enlaces, imagenes, videos y audios.\n\nComandos:\n/stats - Estadisticas\n/tipos - Buscar por tipo\n/recientes - Ultimos 10"
    await update.message.reply_text(text)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = get_statistics(chat_id)
    text = f"Estadisticas\n\nTotal: {data['total']} elementos\n\n"
    if data['by_type']:
        text += "Por tipo:\n"
        for ctype, count in data['by_type']:
            text += f"  {ctype}: {count}\n"
    if data['by_user']:
        text += "\nPor usuario:\n"
        for user, count in data['by_user']:
            text += f"  {user}: {count}\n"
    await update.message.reply_text(text)

async def tipos_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Imagenes", callback_data="type_imagen")],
        [InlineKeyboardButton("Videos", callback_data="type_video")],
        [InlineKeyboardButton("Audios", callback_data="type_audio")],
        [InlineKeyboardButton("Enlaces", callback_data="type_enlace")]
    ]
    await update.message.reply_text("Que tipo queres ver?", reply_markup=InlineKeyboardMarkup(keyboard))

async def recientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    results = search_content(chat_id, limit=10)
    if not results:
        await update.message.reply_text("No hay contenido guardado.")
        return
    text = "Ultimos 10:\n\n"
    for item in results:
        ts = datetime.strptime(item[11], "%Y-%m-%d %H:%M:%S").strftime("%d/%m")
        text += f"{ts} - {item[4]} - {item[5]}\n"
        if item[7]:
            text += f"{item[7]}\n"
    await update.message.reply_text(text)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    if query.data.startswith("type_"):
        content_type = query.data.replace("type_", "")
        results = search_content(chat_id, 'type', content_type, 10)
        if not results:
            await query.edit_message_text(f"No hay {content_type}s.")
            return
        text = f"Ultimos {content_type}s:\n\n"
        for item in results:
            ts = datetime.strptime(item[11], "%Y-%m-%d %H:%M:%S").strftime("%d/%m")
            text += f"{ts} - {item[4]}\n"
            if item[7]:
                text += f"{item[7]}\n"
        await query.edit_message_text(text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Ex-amigos"
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    file_id = update.message.photo[-1].file_id
    caption = update.message.caption
    cid, tags = save_content(chat_id, chat_title, user_id, username, 'imagen', 'Telegram', file_id=file_id, caption=caption)
    await update.message.reply_text(f"Imagen guardada #{cid}", quote=True)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Ex-amigos"
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    file_id = update.message.video.file_id
    caption = update.message.caption
    cid, tags = save_content(chat_id, chat_title, user_id, username, 'video', 'Telegram', file_id=file_id, caption=caption)
    await update.message.reply_text(f"Video guardado #{cid}", quote=True)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Ex-amigos"
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    audio = update.message.audio or update.message.voice
    file_id = audio.file_id
    caption = update.message.caption
    cid, tags = save_content(chat_id, chat_title, user_id, username, 'audio', 'Telegram', file_id=file_id, caption=caption)
    await update.message.reply_text(f"Audio guardado #{cid}", quote=True)

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Ex-amigos"
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    text = update.message.text
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
    if not urls:
        return
    for url in urls:
        source = classify_url(url)
        cid, tags = save_content(chat_id, chat_title, user_id, username, 'enlace', source, url=url, caption=text)
        await update.message.reply_text(f"Enlace guardado #{cid} - {source}", quote=True)

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("tipos", tipos_menu))
    app.add_handler(CommandHandler("recientes", recientes))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & filters.Entity("url"), handle_url))
    print("Bot Ex-amigos iniciado")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
