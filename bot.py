#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bot Clasificador - Grupo Ex-amigos
Germán, Leo y Mario
"""

import sqlite3
from datetime import datetime
from urllib.parse import urlparse
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

TOKEN = "8470535043:AAEafK7ExK2vxMX7w_NbcMQeVuZppzLmUbI"
DB_PATH = "ex_amigos_repo.db"

MIEMBROS = {
    'Germán': '📚',
    'Leo': '🎬',
    'Mario': '🎵'
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            chat_title TEXT,
            user_id INTEGER,
            username TEXT,
            content_type TEXT,
            source TEXT,
            url TEXT,
            file_id TEXT,
            caption TEXT,
            tags TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def classify_url(url):
    domain = urlparse(url).netloc.lower()
    sources = {
        'youtube.com': 'YouTube', 'youtu.be': 'YouTube',
        'instagram.com': 'Instagram', 'twitter.com': 'Twitter/X',
        'x.com': 'Twitter/X', 'facebook.com': 'Facebook',
        'tiktok.com': 'TikTok', 'spotify.com': 'Spotify',
        'soundcloud.com': 'SoundCloud', 'vimeo.com': 'Vimeo',
        'reddit.com': 'Reddit', 'github.com': 'GitHub',
        'drive.google.com': 'Google Drive'
    }
    for key, value in sources.items():
        if key in domain:
            return value
    return 'Web General'

def extract_tags(text):
    if not text:
        return []
    return re.findall(r'#(\w+)', text)

def save_content(chat_id, chat_title, user_id, username, content_type, 
                 source, url=None, file_id=None, caption=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    tags = extract_tags(caption)
    tags_str = ','.join(tags) if tags else ''
    
    cursor.execute('''
        INSERT INTO content (chat_id, chat_title, user_id, username, 
                           content_type, source, url, file_id, caption, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (chat_id, chat_title, user_id, username, content_type, 
          source, url, file_id, caption, tags_str))
    
    conn.commit()
    content_id = cursor.lastrowid
    conn.close()
    return content_id, tags

def get_statistics(chat_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM content WHERE chat_id = ?', (chat_id,))
    total = cursor.fetchone()[0]
    
    cursor.execute('''SELECT content_type, COUNT(*) FROM content 
                     WHERE chat_id = ? GROUP BY content_type''', (chat_id,))
    by_type = cursor.fetchall()
    
    cursor.execute('''SELECT source, COUNT(*) FROM content 
                     WHERE chat_id = ? GROUP BY source 
                     ORDER BY COUNT(*) DESC LIMIT 5''', (chat_id,))
    by_source = cursor.fetchall()
    
    cursor.execute('''SELECT username, COUNT(*) FROM content 
                     WHERE chat_id = ? GROUP BY username
                     ORDER BY COUNT(*) DESC''', (chat_id,))
    by_user = cursor.fetchall()
    
    conn.close()
    return {
        'total': total, 
        'by_type': by_type, 
        'by_source': by_source,
        'by_user': by_user
    }

def search_content(chat_id, query_type=None, query_value=None, limit=15):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if query_type == 'tag':
        cursor.execute('''SELECT * FROM content WHERE chat_id = ? 
                         AND tags LIKE ? ORDER BY timestamp DESC LIMIT ?''',
                      (chat_id, f'%{query_value}%', limit))
    elif query_type == 'type':
        cursor.execute('''SELECT * FROM content WHERE chat_id = ? 
                         AND content_type = ? ORDER BY timestamp DESC LIMIT ?''',
                      (chat_id, query_value, limit))
    elif query_type == 'source':
        cursor.execute('''SELECT * FROM content WHERE chat_id = ? 
                         AND source = ? ORDER BY timestamp DESC LIMIT ?''',
                      (chat_id, query_value, limit))
    elif query_type == 'user':
        cursor.execute('''SELECT * FROM content WHERE chat_id = ? 
                         AND username = ? ORDER BY timestamp DESC LIMIT ?''',
                      (chat_id, query_value, limit))
    else:
        cursor.execute('''SELECT * FROM content WHERE chat_id = ? 
                         ORDER BY timestamp DESC LIMIT ?''', (chat_id, limit))
    
    results = cursor.fetchall()
    conn.close()
    return results

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """🤖 *Bot Clasificador - Ex-amigos*

¡Hola! Soy el archivero digital del grupo.
Organizo todo lo que Germán 📚, Leo 🎬 y Mario 🎵 comparten.

📌 *¿Qué hago?*
- Clasifico enlaces, imágenes, videos y audios
- Identifico fuentes (YouTube, Instagram, etc.)
- Organizo por #etiquetas

🏷️ *Usar etiquetas:*
_"Mirá esto #cine #documental"_

📋 *Comandos:*
/stats - Estadísticas del archivo
/tipos - Buscar por tipo
/miembros - Ver aportes por persona
/recientes - Últimos 10 contenidos

💾 Archivo: ex_amigos_repo.db"""
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = get_statistics(chat_id)
    
    text = f"📊 *Estadísticas - Ex-amigos*\n\n"
    text += f"📦 Total: *{data['total']}* elementos archivados\n\n"
    
    if data['by_type']:
        text += "📑 *Por tipo:*\n"
        icons = {'imagen': '🖼️', 'video': '🎥', 'audio': '🎵', 'enlace': '🔗'}
        for ctype, count in data['by_type']:
            icon = icons.get(ctype, '📄')
            text += f"  {icon} {ctype.capitalize()}: {count}\n"
        text += "\n"
    
    if data['by_user']:
        text += "👥 *Aportes por miembro:*\n"
        for user, count in data['by_user']:
            icon = MIEMBROS.get(user, '👤')
            text += f"  {icon} {user}: {count}\n"
        text += "\n"
    
    if data['by_source']:
        text += "🌐 *Top fuentes:*\n"
        for source, count in data['by_source']:
            text += f"  • {source}: {count}\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def tipos_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🖼️ Imágenes", callback_data="type_imagen")],
        [InlineKeyboardButton("🎥 Videos", callback_data="type_video")],
        [InlineKeyboardButton("🎵 Audios", callback_data="type_audio")],
        [InlineKeyboardButton("🔗 Enlaces", callback_data="type_enlace")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("¿Qué tipo querés ver?", reply_markup=reply_markup)

async def miembros_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 Germán", callback_data="user_Germán")],
        [InlineKeyboardButton("🎬 Leo", callback_data="user_Leo")],
        [InlineKeyboardButton("🎵 Mario", callback_data="user_Mario")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("¿De quién querés ver aportes?", reply_markup=reply_markup)

async def recientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    results = search_content(chat_id, limit=10)
    
    if not results:
        await update.message.reply_text("No hay contenido guardado aún.")
        return
    
    text = "🕐 *Últimos 10 contenidos:*\n\n"
    for item in results:
        ts = datetime.strptime(item[11], "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M")
        user = item[4] or "Anónimo"
        icon = MIEMBROS.get(user, '👤')
        ctype = item[5]
        type_icons = {'imagen': '🖼️', 'video': '🎥', 'audio': '🎵', 'enlace': '🔗'}
        type_icon = type_icons.get(ctype, '📄')
        
        text += f"{type_icon} {ts} | {icon} {user}\n"
        if item[7]:
            text += f"🔗 {item[7]}\n"
        if item[10]:
            text += f"🏷️ {' '.join(['#'+t for t in item[10].split(',')])}\n"
        text += "\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    if query.data.startswith("type_"):
        content_type = query.data.replace("type_", "")
        results = search_content(chat_id, 'type', content_type, 10)
        
        if not results:
            await query.edit_message_text(f"No hay {content_type}s guardados.")
            return
        
        text = f"🔍 *Últimos 10 {content_type}s:*\n\n"
        for item in results:
            ts = datetime.strptime(item[11], "%Y-%m-%d %H:%M:%S").strftime("%d/%m")
            user = item[4] or "Anónimo"
            icon = MIEMBROS.get(user, '👤')
            
            text += f"📅 {ts} | {icon} {user}\n"
            if item[9]:
                cap = (item[9][:40] + "...") if len(item[9]) > 40 else item[9]
                text += f"💬 {cap}\n"
            if item[7]:
                text += f"🔗 {item[7]}\n"
            text += "\n"
        
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data.startswith("user_"):
        username = query.data.replace("user_", "")
        results = search_content(chat_id, 'user', username, 10)
        
        if not results:
            await query.edit_message_text(f"No hay contenido de {username}.")
            return
        
        icon = MIEMBROS.get(username, '👤')
        text = f"🔍 *Aportes de {icon} {username}:*\n\n"
        
        for item in results:
            ts = datetime.strptime(item[11], "%Y-%m-%d %H:%M:%S").strftime("%d/%m")
            ctype = item[5]
            type_icons = {'imagen': '🖼️', 'video': '🎥', 'audio': '🎵', 'enlace': '🔗'}
            type_icon = type_icons.get(ctype, '📄')
            
            text += f"{type_icon} {ts} - {ctype}\n"
            if item[7]:
                text += f"🔗 {item[7]}\n"
            text += "\n"
        
        await query.edit_message_text(text, parse_mode='Markdown')

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Ex-amigos"
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    
    file_id = update.message.photo[-1].file_id
    caption = update.message.caption
    
    cid, tags = save_content(chat_id, chat_title, user_id, username,
                            'imagen', 'Telegram', file_id=file_id, caption=caption)
    
    tag_text = f" | {' '.join(['#'+t for t in tags])}" if tags else ""
    await update.message.reply_text(f"✅ Imagen #{cid} archivada{tag_text}", quote=True)

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Ex-amigos"
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    
    file_id = update.message.video.file_id
    caption = update.message.caption
    
    cid, tags = save_content(chat_id, chat_title, user_id, username,
                            'video', 'Telegram', file_id=file_id, caption=caption)
    
    tag_text = f" | {' '.join(['#'+t for t in tags])}" if tags else ""
    await update.message.reply_text(f"✅ Video #{cid} archivado{tag_text}", quote=True)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or "Ex-amigos"
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    
    audio = update.message.audio or update.message.voice
    file_id = audio.file_id
    caption = update.message.caption
    
    cid, tags = save_content(chat_id, chat_title, user_id, username,
                            'audio', 'Telegram', file_id=file_id, caption=caption)
    
    tag_text = f" | {' '.join(['#'+t for t in tags])}" if tags else ""
    await update.message.reply_text(f"✅ Audio #{cid} archivado{tag_text}", quote=True)

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
        cid, tags = save_content(chat_id, chat_title, user_id, username,
                                'enlace', source, url=url, caption=text)
        
        tag_text = f" | {' '.join(['#'+t for t in tags])}" if tags else ""
        await update.message.reply_text(
            f"✅ Enlace #{cid} archivado\n🌐 {source}{tag_text}",
            quote=True
        )

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("tipos", tipos_menu))
    app.add_handler(CommandHandler("miembros", miembros_menu))
    app.add_handler(CommandHandler("recientes", recientes))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, handle_audio))
    app.add_handler(MessageHandler(filters.TEXT & filters.Entity("url"), handle_url))
    
    print("🤖 Bot Ex-amigos iniciado!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
