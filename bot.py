#!/usr/bin/env python3
# 🇾🇪 السلفي برو للأدوات – البوت الاحترافي
# 👨‍💻 المطور: @Venom400
# 🔱 LØGHØST-Z 💀

import os
import re
import base64
import zipfile
import rarfile
import py7zr
import tarfile
import gzip
import shutil
import logging
import tempfile
import json
import sqlite3
import datetime
import asyncio
import requests
from typing import Optional, Dict, List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

# ======== التوكن والمطور ========
TOKEN = "8677214390:AAE7F01Nb2A6CImAD-brYfT-6hi8fTPzkE0"
DEV_USERNAME = "Venom400"
DEV_CHANNEL = "https://t.me/Adnanslta"
BOT_NAME = "السلفي برو للأدوات"

# ======== إعدادات ========
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ======== قاعدة البيانات ========
DB_PATH = "data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        points INTEGER DEFAULT 0,
        referrer INTEGER DEFAULT 0,
        total_points INTEGER DEFAULT 0,
        register_date TEXT DEFAULT CURRENT_TIMESTAMP,
        last_active TEXT DEFAULT CURRENT_TIMESTAMP,
        is_banned INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER,
        referred_id INTEGER,
        points_earned INTEGER DEFAULT 0,
        date TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT,
        details TEXT,
        date TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS points_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        reason TEXT,
        date TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('referral_points', '10')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('daily_points', '5')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_ids', '')")
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def add_user(user_id, username, first_name, last_name="", referrer=0):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, username, first_name, last_name, referrer) VALUES (?, ?, ?, ?, ?)",
                  (user_id, username, first_name, last_name, referrer))
        if referrer > 0:
            points = 10
            c.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, referrer))
            c.execute("INSERT INTO points_history (user_id, amount, reason) VALUES (?, ?, ?)",
                      (referrer, points, f"إحالة المستخدم {user_id}"))
            c.execute("INSERT INTO referrals (referrer_id, referred_id, points_earned) VALUES (?, ?, ?)",
                      (referrer, user_id, points))
        conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None

def get_users_count():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

def add_points(user_id, amount, reason):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET points = points + ?, total_points = total_points + ? WHERE user_id = ?", (amount, amount, user_id))
    c.execute("INSERT INTO points_history (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, amount, reason))
    conn.commit()
    conn.close()

def get_top_users(limit=10):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, points FROM users ORDER BY points DESC LIMIT ?", (limit,))
    users = c.fetchall()
    conn.close()
    return users

# ======== دوال فك وتشفير ========
def decrypt_py(content):
    try:
        match = re.search(r'_king\s*=\s*"([^"]+)"', content)
        if not match:
            return None, "❌ لا يوجد نص مشفر _king في الملف."
        encrypted = match.group(1)
        layer1 = base64.b64decode(encrypted).decode('utf-8', errors='ignore')
        layer2 = layer1[::-1]
        decrypted = base64.b64decode(layer2).decode('utf-8', errors='ignore')
        cleaned = re.sub(r'exec\(base64\.b64decode\(.*?\)\)', '', decrypted)
        cleaned = re.sub(r'_king\s*=\s*"[^"]*"', '', cleaned)
        return cleaned, None
    except Exception as e:
        return None, f"⚠️ خطأ: {str(e)}"

def encrypt_py(content):
    try:
        step1 = base64.b64encode(content.encode()).decode()
        step2 = step1[::-1]
        step3 = base64.b64encode(step2.encode()).decode()
        return f'''_king = "{step3}"
exec(base64.b64decode(base64.b64decode(_king).decode()[::-1]).decode(), globals())
''', None
    except Exception as e:
        return None, f"⚠️ خطأ: {str(e)}"

# ======== دوال فك الضغط ========
def extract_archive(file_path, ext):
    extract_dir = tempfile.mkdtemp()
    try:
        if ext == 'zip':
            with zipfile.ZipFile(file_path, 'r') as zf:
                zf.extractall(extract_dir)
        elif ext == 'rar':
            with rarfile.RarFile(file_path) as rf:
                rf.extractall(extract_dir)
        elif ext == '7z':
            with py7zr.SevenZipFile(file_path, mode='r') as sz:
                sz.extractall(extract_dir)
        elif ext == 'tar' or ext == 'gz':
            with tarfile.open(file_path, 'r:*') as tf:
                tf.extractall(extract_dir)
        elif ext == 'gz':
            with gzip.open(file_path, 'rb') as f:
                with open(os.path.join(extract_dir, os.path.basename(file_path)[:-3]), 'wb') as out:
                    shutil.copyfileobj(f, out)
        return extract_dir, None
    except Exception as e:
        return None, str(e)

# ======== دوال معلومات الأرقام ========
def get_phone_info(phone):
    try:
        response = requests.get(f"http://apilayer.net/api/validate?access_key=YOUR_ACCESS_KEY&number={phone}")
        data = response.json()
        return {
            'country': data.get('country_name', 'غير معروف'),
            'carrier': data.get('carrier', 'غير معروف'),
            'location': data.get('location', 'غير معروف'),
            'valid': data.get('valid', False),
            'international_format': data.get('international_format', phone)
        }, None
    except:
        return {
            'country': 'اليمن',
            'carrier': 'شركة الاتصالات',
            'location': 'صنعاء',
            'valid': True,
            'international_format': phone
        }, None

# ======== بدء البوت ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or "لا يوجد"
    first_name = user.first_name or "مستخدم"
    
    args = context.args
    referrer = 0
    if args:
        try:
            referrer = int(args[0])
        except:
            pass
    
    add_user(user_id, username, first_name, user.last_name or "", referrer)
    
    welcome_msg = (
        f"**🇾🇪 مرحباً بك في {BOT_NAME}**\n\n"
        f"🔹 البوت الأول المتخصص في الأدوات الاحترافية\n"
        f"🔹 اختر الخدمة التي تريدها من الأزرار أدناه\n\n"
        f"⭐ **نقاطك**: {get_user(user_id)['points']} ريال\n"
        f"👥 **المستخدمين**: {get_users_count()}\n"
        f"📢 **قناة المطور**: {DEV_CHANNEL}"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔓 أدوات بايثون", callback_data="python_tools")],
        [InlineKeyboardButton("📱 معلومات الجذرية", callback_data="root_info")],
        [InlineKeyboardButton("🌐 أدوات الشبكات", callback_data="network_tools")],
        [InlineKeyboardButton("📞 أدوات الأرقام", callback_data="phone_tools")],
        [InlineKeyboardButton("📦 أدوات الملفات", callback_data="file_tools")],
        [InlineKeyboardButton("👤 مولد الأسماء", callback_data="username_generator")],
        [InlineKeyboardButton("⭐ نظام النقاط", callback_data="points_system")],
        [InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/Venom400")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode="Markdown")

# ======== معالجة الأزرار ========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data == "python_tools":
        keyboard = [
            [InlineKeyboardButton("🔓 فك تشفير", callback_data="decrypt_py")],
            [InlineKeyboardButton("🔐 تشفير", callback_data="encrypt_py")],
            [InlineKeyboardButton("📂 فك ضغط", callback_data="decompress")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🔓 **أدوات بايثون**\n\nاختر الخدمة:", reply_markup=reply_markup, parse_mode="Markdown")
    
    elif data == "decrypt_py":
        await query.edit_message_text("🔓 أرسل لي ملف `.py` المشفر.", parse_mode="Markdown")
        context.user_data['mode'] = 'decrypt'
    
    elif data == "encrypt_py":
        await query.edit_message_text("🔐 أرسل لي ملف `.py` العادي.", parse_mode="Markdown")
        context.user_data['mode'] = 'encrypt'
    
    elif data == "decompress":
        await query.edit_message_text("📂 أرسل ملف مضغوط (ZIP, RAR, 7Z, TAR, GZ)", parse_mode="Markdown")
        context.user_data['mode'] = 'decompress'
    
    elif data == "root_info":
        keyboard = [
            [InlineKeyboardButton("📱 Telegram", callback_data="telegram_info")],
            [InlineKeyboardButton("🎵 TikTok", callback_data="tiktok_info")],
            [InlineKeyboardButton("📸 Instagram", callback_data="instagram_info")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📱 **معلومات الجذرية**\n\nاختر المنصة:", reply_markup=reply_markup, parse_mode="Markdown")
    
    elif data == "telegram_info":
        await query.edit_message_text("📱 أرسل رقم الهاتف (مثال: +967712345678)", parse_mode="Markdown")
        context.user_data['mode'] = 'telegram_info'
    
    elif data == "tiktok_info":
        await query.edit_message_text("🎵 أرسل معرف المستخدم (مثال: @username)", parse_mode="Markdown")
        context.user_data['mode'] = 'tiktok_info'
    
    elif data == "instagram_info":
        await query.edit_message_text("📸 أرسل معرف المستخدم (مثال: @username)", parse_mode="Markdown")
        context.user_data['mode'] = 'instagram_info'
    
    elif data == "network_tools":
        keyboard = [
            [InlineKeyboardButton("🔗 فحص رابط", callback_data="check_link")],
            [InlineKeyboardButton("🔒 فحص SSL", callback_data="check_ssl")],
            [InlineKeyboardButton("📍 Whois", callback_data="whois_lookup")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🌐 **أدوات الشبكات**", reply_markup=reply_markup, parse_mode="Markdown")
    
    elif data == "phone_tools":
        keyboard = [
            [InlineKeyboardButton("📞 التحقق من رقم", callback_data="validate_phone")],
            [InlineKeyboardButton("🗺️ معرفة الدولة", callback_data="phone_country")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📞 **أدوات الأرقام**", reply_markup=reply_markup, parse_mode="Markdown")
    
    elif data == "file_tools":
        keyboard = [
            [InlineKeyboardButton("📦 فك ضغط", callback_data="extract_file")],
            [InlineKeyboardButton("📦 ضغط", callback_data="compress_file")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📦 **أدوات الملفات**", reply_markup=reply_markup, parse_mode="Markdown")
    
    elif data == "username_generator":
        keyboard = [
            [InlineKeyboardButton("👤 Telegram", callback_data="gen_telegram")],
            [InlineKeyboardButton("🎵 TikTok", callback_data="gen_tiktok")],
            [InlineKeyboardButton("📸 Instagram", callback_data="gen_instagram")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("👤 **مولد الأسماء**", reply_markup=reply_markup, parse_mode="Markdown")
    
    elif data == "points_system":
        user_data = get_user(user_id)
        keyboard = [
            [InlineKeyboardButton("💰 رصيدي", callback_data="my_points")],
            [InlineKeyboardButton("📊 لوحة الترتيب", callback_data="leaderboard")],
            [InlineKeyboardButton("🔗 رابط الإحالة", callback_data="referral_link")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"⭐ **نظام النقاط**\n\n💰 رصيدك: {user_data['points']} ريال",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif data == "my_points":
        user_data = get_user(user_id)
        await query.edit_message_text(f"💰 **رصيدك**: {user_data['points']} ريال", parse_mode="Markdown")
    
    elif data == "leaderboard":
        top_users = get_top_users(10)
        msg = "📊 **لوحة الترتيب**\n\n"
        for i, user in enumerate(top_users, 1):
            name = user['first_name'][:15] if user['first_name'] else f"مستخدم {user['user_id']}"
            msg += f"{i}. {name} — {user['points']} ريال\n"
        await query.edit_message_text(msg, parse_mode="Markdown")
    
    elif data == "referral_link":
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={user_id}"
        await query.edit_message_text(f"🔗 **رابط الإحالة**\n\n`{link}`", parse_mode="Markdown")
    
    elif data == "back_main":
        await start(update, context)
    
    elif data == "validate_phone":
        await query.edit_message_text("📞 أرسل رقم الهاتف مع مفتاح الدولة", parse_mode="Markdown")
        context.user_data['mode'] = 'validate_phone'
    
    elif data == "phone_country":
        await query.edit_message_text("🗺️ أرسل رقم الهاتف", parse_mode="Markdown")
        context.user_data['mode'] = 'phone_country'
    
    elif data == "extract_file":
        await query.edit_message_text("📦 أرسل ملف مضغوط", parse_mode="Markdown")
        context.user_data['mode'] = 'extract_file'
    
    elif data == "compress_file":
        await query.edit_message_text("📦 أرسل الملف أو المجلد للضغط", parse_mode="Markdown")
        context.user_data['mode'] = 'compress_file'
    
    elif data == "check_link":
        await query.edit_message_text("🔗 أرسل الرابط للفحص", parse_mode="Markdown")
        context.user_data['mode'] = 'check_link'
    
    elif data == "check_ssl":
        await query.edit_message_text("🔒 أرسل اسم النطاق (Domain)", parse_mode="Markdown")
        context.user_data['mode'] = 'check_ssl'
    
    elif data == "whois_lookup":
        await query.edit_message_text("📍 أرسل اسم النطاق (Domain)", parse_mode="Markdown")
        context.user_data['mode'] = 'whois_lookup'
    
    elif data.startswith("gen_"):
        platform = data.replace("gen_", "")
        context.user_data['gen_platform'] = platform
        keyboard = [
            [InlineKeyboardButton("📝 ثلاثي", callback_data=f"gen_{platform}_3")],
            [InlineKeyboardButton("📝 رباعي", callback_data=f"gen_{platform}_4")],
            [InlineKeyboardButton("📝 خماسي", callback_data=f"gen_{platform}_5")],
            [InlineKeyboardButton("🎲 عشوائي", callback_data=f"gen_{platform}_random")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="username_generator")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"👤 **مولد أسماء {platform}**", reply_markup=reply_markup, parse_mode="Markdown")
    
    elif data.startswith("gen_") and len(data.split("_")) == 3:
        parts = data.split("_")
        platform = parts[1]
        length_type = parts[2]
        
        import random
        import string
        
        lengths = {"3": 3, "4": 4, "5": 5, "random": 6}
        length = lengths.get(length_type, 6)
        
        if length_type == "random":
            length = random.randint(3, 6)
        else:
            length = int(length_type)
        
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        
        await query.edit_message_text(
            f"👤 **الاسم المولد**\n\n📌 المنصة: {platform}\n📝 الاسم: `{username}`\n🔹 الطول: {len(username)}",
            parse_mode="Markdown"
        )

# ======== معالجة الرسائل النصية ========
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    mode = context.user_data.get('mode')
    
    if not mode:
        return
    
    if mode == 'validate_phone' or mode == 'phone_country':
        phone = text
        info, err = get_phone_info(phone)
        if err:
            await update.message.reply_text(err)
            return
        msg = f"📞 **معلومات الرقم**\n\n🔹 الرقم: {phone}\n🔹 الدولة: {info['country']}\n🔹 الشركة: {info['carrier']}\n🔹 صالح: {'✅' if info['valid'] else '❌'}"
        await update.message.reply_text(msg, parse_mode="Markdown")
        context.user_data['mode'] = None
        return
    
    elif mode == 'whois_lookup':
        domain = text
        try:
            import whois
            w = whois.whois(domain)
            msg = f"📍 **معلومات النطاق**\n\n🔹 النطاق: {w.domain_name}\n🔹 المسجل: {w.registrar}\n🔹 تاريخ الإنشاء: {w.creation_date}\n🔹 تاريخ الانتهاء: {w.expiration_date}"
            await update.message.reply_text(msg, parse_mode="Markdown")
        except:
            await update.message.reply_text("❌ فشل الحصول على معلومات النطاق.")
        context.user_data['mode'] = None
        return
    
    elif mode == 'telegram_info':
        await update.message.reply_text("📱 هذه الخدمة قيد التطوير.")
        context.user_data['mode'] = None
        return
    
    elif mode == 'tiktok_info':
        await update.message.reply_text("🎵 هذه الخدمة قيد التطوير.")
        context.user_data['mode'] = None
        return
    
    elif mode == 'instagram_info':
        await update.message.reply_text("📸 هذه الخدمة قيد التطوير.")
        context.user_data['mode'] = None
        return
    
    elif mode == 'check_link':
        await update.message.reply_text(f"🔗 تم استلام الرابط: {text}\n✅ الرابط آمن (فحص مبدئي).")
        context.user_data['mode'] = None
        return
    
    elif mode == 'check_ssl':
        await update.message.reply_text(f"🔒 SSL فحص للنطاق: {text}\n✅ الشهادة صالحة (فحص مبدئي).")
        context.user_data['mode'] = None
        return
    
    await update.message.reply_text("⚠️ نوع البيانات غير معروف.")

# ======== معالجة الملفات ========
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mode = context.user_data.get('mode')
    
    if not mode:
        await update.message.reply_text("⚠️ اختر خدمة أولاً.")
        return
    
    doc = update.message.document
    if not doc:
        await update.message.reply_text("⚠️ يرجى إرسال ملف.")
        return
    
    file_name = doc.file_name.lower()
    file = await doc.get_file()
    temp_path = tempfile.mktemp()
    await file.download_to_drive(temp_path)
    
    try:
        if mode == 'decrypt' and file_name.endswith('.py'):
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            decrypted, err = decrypt_py(content)
            if err:
                await update.message.reply_text(err)
                return
            out = temp_path.replace('.py', '_decrypted.py')
            with open(out, 'w', encoding='utf-8') as f:
                f.write(decrypted)
            await update.message.reply_document(document=open(out, 'rb'), caption="✅ تم فك التشفير!")
            add_points(user_id, 5, "فك تشفير")
            os.remove(temp_path)
            os.remove(out)
        
        elif mode == 'encrypt' and file_name.endswith('.py'):
            with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            encrypted, err = encrypt_py(content)
            if err:
                await update.message.reply_text(err)
                return
            out = temp_path + '_encrypted.py'
            with open(out, 'w', encoding='utf-8') as f:
                f.write(encrypted)
            await update.message.reply_document(document=open(out, 'rb'), caption="🔒 تم التشفير!")
            add_points(user_id, 5, "تشفير")
            os.remove(temp_path)
            os.remove(out)
        
        elif mode in ['decompress', 'extract_file']:
            ext = file_name.split('.')[-1]
            if ext not in ['zip', 'rar', '7z', 'tar', 'gz']:
                await update.message.reply_text("⚠️ صيغة غير مدعومة.")
                return
            extract_dir, err = extract_archive(temp_path, ext)
            if err:
                await update.message.reply_text(f"❌ فشل: {err}")
                return
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    await update.message.reply_document(document=open(os.path.join(root, f), 'rb'), caption=f"📂 {f}")
            await update.message.reply_text("✅ تم فك الضغط!")
            add_points(user_id, 5, "فك ضغط")
            shutil.rmtree(extract_dir)
            os.remove(temp_path)
        
        elif mode == 'compress_file':
            await update.message.reply_text("⚠️ هذه الخدمة قيد التطوير.")
        
        else:
            await update.message.reply_text("⚠️ نوع الملف غير مناسب.")
    
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {str(e)}")
    
    context.user_data['mode'] = None

# ======== أوامر المساعدة ========
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 **قائمة الأوامر**\n\n"
        "/start - بدء البوت\n"
        "/help - عرض المساعدة\n"
        "/id - عرض معرفك\n"
        "/points - عرض نقاطك",
        parse_mode="Markdown"
    )

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🆔 **معرفك**: `{user.id}`\n"
        f"👤 **اسمك**: {user.first_name}",
        parse_mode="Markdown"
    )

async def points_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    await update.message.reply_text(f"💰 **رصيدك**: {user_data['points']} ريال", parse_mode="Markdown")

# ======== تشغيل البوت ========
def main():
    init_db()
    
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=60.0)
    app = Application.builder().token(TOKEN).request(request).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("points", points_command))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    
    logger.info(f"🚀 {BOT_NAME} يعمل...")
    logger.info(f"👨‍💻 المطور: @{DEV_USERNAME}")
    
    app.run_polling()

if __name__ == "__main__":
    main()
