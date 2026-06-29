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
import hashlib
import datetime
import asyncio
import requests
from typing import Optional, Dict, List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
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
    """تهيئة قاعدة البيانات"""
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
    
    # إعدادات افتراضية
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('referral_points', '10')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('daily_points', '5')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_ids', '')")
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ======== دوال قاعدة البيانات ========
def add_user(user_id, username, first_name, last_name="", referrer=0):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute("INSERT INTO users (user_id, username, first_name, last_name, referrer) VALUES (?, ?, ?, ?, ?)",
                  (user_id, username, first_name, last_name, referrer))
        if referrer > 0:
            # إضافة نقاط للمُحيل
            points = get_setting('referral_points', 10)
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

def get_setting(key, default=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    if result:
        try:
            return int(result[0])
        except:
            return result[0]
    return default

def set_setting(key, value):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def add_points(user_id, amount, reason):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET points = points + ?, total_points = total_points + ? WHERE user_id = ?", (amount, amount, user_id))
    c.execute("INSERT INTO points_history (user_id, amount, reason) VALUES (?, ?, ?)", (user_id, amount, reason))
    conn.commit()
    conn.close()

def log_action(user_id, action, details=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)", (user_id, action, details))
    conn.commit()
    conn.close()

def get_top_users(limit=10):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, points FROM users ORDER BY points DESC LIMIT ?", (limit,))
    users = c.fetchall()
    conn.close()
    return users

# ============================================
# 1. دوال فك وتشفير بايثون
# ============================================
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

# ============================================
# 2. دوال فك الضغط
# ============================================
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

def compress_archive(source_path, format):
    output = tempfile.mktemp(suffix=f'.{format}')
    try:
        if format == 'zip':
            with zipfile.ZipFile(output, 'w') as zf:
                if os.path.isdir(source_path):
                    for root, _, files in os.walk(source_path):
                        for f in files:
                            zf.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), source_path))
                else:
                    zf.write(source_path, os.path.basename(source_path))
        elif format == 'tar':
            with tarfile.open(output, 'w') as tf:
                tf.add(source_path, arcname=os.path.basename(source_path))
        return output, None
    except Exception as e:
        return None, str(e)

# ============================================
# 3. دوال معلومات الأرقام
# ============================================
def get_phone_info(phone):
    try:
        # استخدام API خارجية للحصول على معلومات الرقم
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
        # معلومات افتراضية في حالة فشل API
        return {
            'country': 'اليمن',
            'carrier': 'شركة الاتصالات',
            'location': 'صنعاء',
            'valid': True,
            'international_format': phone
        }, None

# ============================================
# 4. دوال معلومات النطاق
# ============================================
def get_domain_info(domain):
    try:
        import whois
        w = whois.whois(domain)
        return {
            'domain_name': w.domain_name,
            'registrar': w.registrar,
            'creation_date': str(w.creation_date),
            'expiration_date': str(w.expiration_date),
            'name_servers': w.name_servers,
            'status': w.status
        }, None
    except:
        return None, "❌ فشل الحصول على معلومات النطاق."

# ============================================
# 5. القائمة الرئيسية
# ============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username or "لا يوجد"
    first_name = user.first_name or "مستخدم"
    
    # معالجة الإحالة
    args = context.args
    referrer = 0
    if args:
        try:
            referrer = int(args[0])
        except:
            pass
    
    add_user(user_id, username, first_name, user.last_name or "", referrer)
    log_action(user_id, "start", "بدأ البوت")
    
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

# ============================================
# 6. معالجة الأزرار
# ============================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data == "python_tools":
        keyboard = [
            [InlineKeyboardButton("🔓 فك تشفير", callback_data="decrypt_py")],
            [InlineKeyboardButton("🔐 تشفير", callback_data="encrypt_py")],
            [InlineKeyboardButton("📦 ضغط مشروع", callback_data="compress_project")],
            [InlineKeyboardButton("📂 فك ضغط", callback_data="decompress")],
            [InlineKeyboardButton("🔍 فحص سلامة", callback_data="check_integrity")],
            [InlineKeyboardButton("📋 تحليل مكتبات", callback_data="analyze_libs")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔓 **أدوات بايثون**\n\nاختر الخدمة المطلوبة:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif data == "decrypt_py":
        await query.edit_message_text(
            "🔓 **فك تشفير بايثون**\n\n"
            "📌 أرسل لي ملف `.py` المشفر وسأفكه لك فوراً.\n"
            "⚠️ الملف يجب أن يحتوي على نص مشفر بنمط `_king`",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'decrypt'
    
    elif data == "encrypt_py":
        await query.edit_message_text(
            "🔐 **تشفير بايثون**\n\n"
            "📌 أرسل لي ملف `.py` العادي وسأقوم بتشفيره بنمط `_king`",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'encrypt'
    
    elif data == "compress_project":
        await query.edit_message_text(
            "📦 **ضغط مشروع بايثون**\n\n"
            "📌 أرسل لي مجلد المشروع (مضغوطاً) أو اختر صيغة الضغط:\n"
            "🔹 `zip` - الأكثر شيوعاً\n"
            "🔹 `tar` - للأنظمة الشبيهة بيونكس",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'compress'
    
    elif data == "decompress":
        await query.edit_message_text(
            "📂 **فك ضغط الملفات**\n\n"
            "📌 أرسل لي ملف مضغوط بصيغة:\n"
            "`ZIP` - `RAR` - `7Z` - `TAR` - `GZ`",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'decompress'
    
    elif data == "check_integrity":
        await query.edit_message_text(
            "🔍 **فحص سلامة الملفات**\n\n"
            "📌 أرسل لي ملف `.py` وسأقوم بفحصه بحثاً عن:\n"
            "✅ أخطاء بناء الجملة\n"
            "✅ مشاكل في الاستيرادات\n"
            "✅ ثغرات أمنية محتملة",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'check_integrity'
    
    elif data == "analyze_libs":
        await query.edit_message_text(
            "📋 **تحليل المكتبات**\n\n"
            "📌 أرسل لي ملف `.py` وسأقوم بتحليل:\n"
            "✅ المكتبات المستخدمة\n"
            "✅ الإصدارات المطلوبة\n"
            "✅ التبعيات",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'analyze_libs'
    
    elif data == "root_info":
        keyboard = [
            [InlineKeyboardButton("📱 معلومات Telegram", callback_data="telegram_info")],
            [InlineKeyboardButton("🎵 معلومات TikTok", callback_data="tiktok_info")],
            [InlineKeyboardButton("📸 معلومات Instagram", callback_data="instagram_info")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📱 **معلومات الجذرية**\n\nاختر المنصة:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif data == "telegram_info":
        await query.edit_message_text(
            "📱 **معلومات Telegram**\n\n"
            "📌 أرسل رقم الهاتف (مع مفتاح الدولة)\n"
            "مثال: `+967712345678`\n\n"
            "⚠️ سيتم عرض:\n"
            "🔹 الاسم الكامل\n"
            "🔹 الموقع\n"
            "🔹 القنوات المشترك فيها\n"
            "🔹 رقم الهاتف (إن كان مخفياً)",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'telegram_info'
    
    elif data == "tiktok_info":
        await query.edit_message_text(
            "🎵 **معلومات TikTok**\n\n"
            "📌 أرسل معرف المستخدم (Username)\n"
            "مثال: `@username`\n\n"
            "⚠️ سيتم عرض:\n"
            "🔹 الاسم الكامل\n"
            "🔹 البايو\n"
            "🔹 عدد المتابعين\n"
            "🔹 عدد الفيديوهات\n"
            "🔹 عدد الإعجابات",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'tiktok_info'
    
    elif data == "instagram_info":
        await query.edit_message_text(
            "📸 **معلومات Instagram**\n\n"
            "📌 أرسل معرف المستخدم (Username)\n"
            "مثال: `@username`\n\n"
            "⚠️ سيتم عرض:\n"
            "🔹 الاسم الكامل\n"
            "🔹 البايو\n"
            "🔹 عدد المتابعين\n"
            "🔹 عدد المنشورات\n"
            "🔹 تاريخ الإنشاء",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'instagram_info'
    
    elif data == "network_tools":
        keyboard = [
            [InlineKeyboardButton("🔗 فحص رابط", callback_data="check_link")],
            [InlineKeyboardButton("🔒 فحص SSL", callback_data="check_ssl")],
            [InlineKeyboardButton("🌐 DNS Lookup", callback_data="dns_lookup")],
            [InlineKeyboardButton("📍 Whois", callback_data="whois_lookup")],
            [InlineKeyboardButton("📡 Ping", callback_data="ping_host")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🌐 **أدوات الشبكات**\n\nاختر الخدمة:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif data == "phone_tools":
        keyboard = [
            [InlineKeyboardButton("📞 التحقق من رقم", callback_data="validate_phone")],
            [InlineKeyboardButton("🗺️ معرفة الدولة", callback_data="phone_country")],
            [InlineKeyboardButton("📡 معرفة الشركة", callback_data="phone_carrier")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📞 **أدوات الأرقام**\n\nاختر الخدمة:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif data == "file_tools":
        keyboard = [
            [InlineKeyboardButton("📦 فك ضغط", callback_data="extract_file")],
            [InlineKeyboardButton("📦 ضغط", callback_data="compress_file")],
            [InlineKeyboardButton("🔄 تحويل امتداد", callback_data="convert_ext")],
            [InlineKeyboardButton("📋 عرض المحتويات", callback_data="list_archive")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📦 **أدوات الملفات**\n\nاختر الخدمة:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif data == "username_generator":
        keyboard = [
            [InlineKeyboardButton("👤 Telegram", callback_data="gen_telegram")],
            [InlineKeyboardButton("🎵 TikTok", callback_data="gen_tiktok")],
            [InlineKeyboardButton("📸 Instagram", callback_data="gen_instagram")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "👤 **مولد أسماء المستخدمين**\n\nاختر المنصة:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif data == "points_system":
        user_data = get_user(user_id)
        keyboard = [
            [InlineKeyboardButton("💰 رصيدي", callback_data="my_points")],
            [InlineKeyboardButton("📊 لوحة الترتيب", callback_data="leaderboard")],
            [InlineKeyboardButton("🎁 استبدال النقاط", callback_data="redeem_points")],
            [InlineKeyboardButton("🔗 رابط الإحالة", callback_data="referral_link")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"⭐ **نظام النقاط**\n\n"
            f"💰 رصيدك: {user_data['points']} ريال\n"
            f"📈 إجمالي النقاط: {user_data['total_points']}\n"
            f"👥 المحالون: ...\n\n"
            f"🔹 احصل على نقاط عند:\n"
            f"✅ استخدام البوت: +5 ريال يومياً\n"
            f"✅ دعوة الأصدقاء: +10 ريال لكل مدعو",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif data == "my_points":
        user_data = get_user(user_id)
        await query.edit_message_text(
            f"💰 **رصيدك الحالي**: {user_data['points']} ريال\n"
            f"📈 **إجمالي النقاط**: {user_data['total_points']} ريال",
            parse_mode="Markdown"
        )
    
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
        await query.edit_message_text(
            f"🔗 **رابط الإحالة الخاص بك**\n\n"
            f"`{link}`\n\n"
            f"⭐ ستحصل على 10 ريال لكل مدعو!",
            parse_mode="Markdown"
        )
    
    elif data == "redeem_points":
        await query.edit_message_text(
            "🎁 **استبدال النقاط**\n\n"
            "📌 قريباً سيتم إضافة المتجر...",
            parse_mode="Markdown"
        )
    
    elif data == "back_main":
        await start(update, context)
    
    elif data == "validate_phone":
        await query.edit_message_text(
            "📞 **التحقق من رقم الهاتف**\n\n"
            "📌 أرسل رقم الهاتف مع مفتاح الدولة\n"
            "مثال: `+967712345678`",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'validate_phone'
    
    elif data == "phone_country":
        await query.edit_message_text(
            "🗺️ **معرفة الدولة**\n\n"
            "📌 أرسل رقم الهاتف مع مفتاح الدولة",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'phone_country'
    
    elif data == "phone_carrier":
        await query.edit_message_text(
            "📡 **معرفة شركة الاتصالات**\n\n"
            "📌 أرسل رقم الهاتف مع مفتاح الدولة",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'phone_carrier'
    
    elif data == "extract_file":
        await query.edit_message_text(
            "📦 **فك ضغط الملفات**\n\n"
            "📌 أرسل ملف مضغوط بصيغة:\n"
            "`ZIP` - `RAR` - `7Z` - `TAR` - `GZ`",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'extract_file'
    
    elif data == "compress_file":
        await query.edit_message_text(
            "📦 **ضغط الملفات**\n\n"
            "📌 أرسل الملف أو المجلد المطلوب ضغطه\n"
            "🔹 اختر الصيغة: `zip` أو `tar`",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'compress_file'
    
    elif data == "convert_ext":
        await query.edit_message_text(
            "🔄 **تحويل الامتداد**\n\n"
            "📌 أرسل الملف مع الامتداد الجديد\n"
            "مثال: `file.py` -> `file.txt`",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'convert_ext'
    
    elif data == "list_archive":
        await query.edit_message_text(
            "📋 **عرض محتويات الأرشيف**\n\n"
            "📌 أرسل ملف مضغوط لعرض محتوياته",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'list_archive'
    
    elif data.startswith("gen_"):
        platform = data.replace("gen_", "")
        context.user_data['gen_platform'] = platform
        keyboard = [
            [InlineKeyboardButton("📝 ثلاثي", callback_data=f"gen_{platform}_3")],
            [InlineKeyboardButton("📝 رباعي", callback_data=f"gen_{platform}_4")],
            [InlineKeyboardButton("📝 خماسي", callback_data=f"gen_{platform}_5")],
            [InlineKeyboardButton("🎲 عشوائي", callback_data=f"gen_{platform}_random")],
            [InlineKeyboardButton("✨ مزخرف", callback_data=f"gen_{platform}_decorated")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="username_generator")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"👤 **مولد أسماء {platform}**\n\nاختر نوع الاسم:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    elif data.startswith("gen_") and len(data.split("_")) == 3:
        parts = data.split("_")
        platform = parts[1]
        length_type = parts[2]
        
        lengths = {"3": 3, "4": 4, "5": 5, "random": 6}
        length = lengths.get(length_type, 6)
        
        import random
        import string
        
        if length_type == "random":
            length = random.randint(3, 6)
        
        if length_type == "decorated":
            prefix = random.choice(["𝓧", "𝓐", "𝓚", "𝓢", "𝓜", "𝓑", "𝓓", "𝓗"])
            suffix = random.choice(["𝓧", "𝓐", "𝓚", "𝓢", "𝓜", "𝓑", "𝓓", "𝓗"])
            letters = ''.join(random.choices(string.ascii_letters, k=length-2))
            username = f"{prefix}{letters}{suffix}"
        else:
            username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        
        await query.edit_message_text(
            f"👤 **الاسم المولد**\n\n"
            f"📌 المنصة: {platform}\n"
            f"📝 الاسم: `{username}`\n"
            f"🔹 الطول: {len(username)}\n\n"
            f"🔗 [فتح في {platform}](https://t.me/{username})",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
    
    elif data == "check_link":
        await query.edit_message_text(
            "🔗 **فحص الرابط**\n\n"
            "📌 أرسل الرابط للفحص",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'check_link'
    
    elif data == "check_ssl":
        await query.edit_message_text(
            "🔒 **فحص SSL**\n\n"
            "📌 أرسل اسم النطاق (Domain)",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'check_ssl'
    
    elif data == "dns_lookup":
        await query.edit_message_text(
            "🌐 **DNS Lookup**\n\n"
            "📌 أرسل اسم النطاق (Domain)",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'dns_lookup'
    
    elif data == "whois_lookup":
        await query.edit_message_text(
            "📍 **Whois Lookup**\n\n"
            "📌 أرسل اسم النطاق (Domain)",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'whois_lookup'
    
    elif data == "ping_host":
        await query.edit_message_text(
            "📡 **Ping**\n\n"
            "📌 أرسل اسم المضيف (Hostname) أو IP",
            parse_mode="Markdown"
        )
        context.user_data['mode'] = 'ping_host'

# ============================================
# 7. معالجة الرسائل النصية
# ============================================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    mode = context.user_data.get('mode')
    
    if not mode:
        return
    
    # معالجة أوامر المطور
    if user_id == 8677214390:  # استبدل بمعرف المطور
        if text.startswith('/broadcast'):
            msg = text.replace('/broadcast', '').strip()
            if msg:
                conn = get_db()
                c = conn.cursor()
                c.execute("SELECT user_id FROM users")
                users = c.fetchall()
                conn.close()
                sent = 0
                for user in users:
                    try:
                        await context.bot.send_message(user[0], f"📢 **إذاعة من المطور**\n\n{msg}", parse_mode="Markdown")
                        sent += 1
                        await asyncio.sleep(0.1)
                    except:
                        pass
                await update.message.reply_text(f"✅ تم إرسال الإذاعة إلى {sent} مستخدم.")
            return
        
        elif text.startswith('/add_points'):
            parts = text.split()
            if len(parts) == 3:
                try:
                    target_id = int(parts[1])
                    amount = int(parts[2])
                    add_points(target_id, amount, "إضافة من المطور")
                    await update.message.reply_text(f"✅ تم إضافة {amount} ريال للمستخدم {target_id}.")
                except:
                    await update.message.reply_text("❌ استخدام: /add_points <user_id> <amount>")
            return
        
        elif text.startswith('/ban'):
            parts = text.split()
            if len(parts) == 2:
                try:
                    target_id = int(parts[1])
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (target_id,))
                    conn.commit()
                    conn.close()
                    await update.message.reply_text(f"✅ تم حظر المستخدم {target_id}.")
                except:
                    await update.message.reply_text("❌ استخدام: /ban <user_id>")
            return
        
        elif text.startswith('/unban'):
            parts = text.split()
            if len(parts) == 2:
                try:
                    target_id = int(parts[1])
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (target_id,))
                    conn.commit()
                    conn.close()
                    await update.message.reply_text(f"✅ تم إلغاء حظر المستخدم {target_id}.")
                except:
                    await update.message.reply_text("❌ استخدام: /unban <user_id>")
            return
        
        elif text.startswith('/stats'):
            users_count = get_users_count()
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT SUM(points) FROM users")
            total_points = c.fetchone()[0] or 0
            conn.close()
            await update.message.reply_text(
                f"📊 **إحصائيات البوت**\n\n"
                f"👥 عدد المستخدمين: {users_count}\n"
                f"⭐ إجمالي النقاط: {total_points}\n"
                f"📅 آخر تحديث: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
                parse_mode="Markdown"
            )
            return
    
    # معالجة الأرقام
    if mode in ['validate_phone', 'phone_country', 'phone_carrier']:
        phone = text
        info, err = get_phone_info(phone)
        if err:
            await update.message.reply_text(err)
            return
        msg = f"📞 **معلومات الرقم**\n\n"
        msg += f"🔹 الرقم: {phone}\n"
        msg += f"🔹 الدولة: {info['country']}\n"
        msg += f"🔹 الشركة: {info['carrier']}\n"
        msg += f"🔹 الموقع: {info['location']}\n"
        msg += f"🔹 صالح: {'✅' if info['valid'] else '❌'}\n"
        msg += f"🔹 التنسيق الدولي: {info['international_format']}"
        await update.message.reply_text(msg, parse_mode="Markdown")
        context.user_data['mode'] = None
        return
    
    # معالجة النطاقات
    if mode in ['check_ssl', 'dns_lookup', 'whois_lookup', 'ping_host']:
        domain = text
        if mode == 'whois_lookup':
            info, err = get_domain_info(domain)
            if err:
                await update.message.reply_text(err)
                return
            msg = f"📍 **معلومات النطاق**\n\n"
            msg += f"🔹 النطاق: {info['domain_name']}\n"
            msg += f"🔹 المسجل: {info['registrar']}\n"
            msg += f"🔹 تاريخ الإنشاء: {info['creation_date']}\n"
            msg += f"🔹 تاريخ الانتهاء: {info['expiration_date']}\n"
            msg += f"🔹 خوادم الأسماء: {', '.join(info['name_servers'] or [])}"
            await update.message.reply_text(msg, parse_mode="Markdown")
        elif mode == 'dns_lookup':
            try:
                import socket
                ip = socket.gethostbyname(domain)
                await update.message.reply_text(f"🌐 **DNS Lookup**\n\n🔹 النطاق: {domain}\n🔹 IP: {ip}", parse_mode="Markdown")
            except:
                await update.message.reply_text("❌ فشل العثور على IP للنطاق.")
        elif mode == 'ping_host':
            try:
                import subprocess
                import platform
                param = '-n' if platform.system().lower() == 'windows' else '-c'
                cmd = ['ping', param, '2', domain]
                result = subprocess.run(cmd, capture_output=True, text=True)
                await update.message.reply_text(f"📡 **Ping**\n\n```{result.stdout[:500]}```", parse_mode="Markdown")
            except:
                await update.message.reply_text("❌ فشل تنفيذ الأمر.")
        elif mode == 'check_ssl':
            try:
                import ssl
                import socket
                context_ssl = ssl.create_default_context()
                with context_ssl.wrap_socket(socket.socket(), server_hostname=domain) as s:
                    s.connect((domain, 443))
                    cert = s.getpeercert()
                    msg = f"🔒 **معلومات SSL**\n\n"
                    msg += f"🔹 النطاق: {domain}\n"
                    msg += f"🔹 المُصدر: {cert.get('issuer')}\n"
                    msg += f"🔹 تاريخ الانتهاء: {cert.get('notAfter')}"
                    await update.message.reply_text(msg, parse_mode="Markdown")
            except:
                await update.message.reply_text("❌ فشل الحصول على معلومات SSL.")
        context.user_data['mode'] = None
        return
    
    # معالجة الفيديو
    if mode == 'tiktok_info':
        await update.message.reply_text("🎵 جاري الحصول على معلومات TikTok...\n⚠️ هذه الخدمة قيد التطوير.")
        context.user_data['mode'] = None
        return
    
    if mode == 'instagram_info':
        await update.message.reply_text("📸 جاري الحصول على معلومات Instagram...\n⚠️ هذه الخدمة قيد التطوير.")
        context.user_data['mode'] = None
        return
    
    if mode == 'telegram_info':
        await update.message.reply_text("📱 جاري الحصول على معلومات Telegram...\n⚠️ هذه الخدمة قيد التطوير.")
        context.user_data['mode'] = None
        return
    
    await update.message.reply_text("⚠️ نوع البيانات غير معروف. حاول مرة أخرى أو اختر خدمة جديدة.")

# ============================================
# 8. معالجة الملفات
# ============================================
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mode = context.user_data.get('mode')
    
    if not mode:
        await update.message.reply_text("⚠️ اختر خدمة أولاً من القائمة.")
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
            await update.message.reply_document(
                document=open(out, 'rb'),
                caption="✅ تم فك التشفير بنجاح!"
            )
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
            await update.message.reply_document(
                document=open(out, 'rb'),
                caption="🔒 تم التشفير بنجاح!"
            )
            add_points(user_id, 5, "تشفير")
            os.remove(temp_path)
            os.remove(out)
        
        elif mode in ['decompress', 'extract_file']:
            ext = file_name.split('.')[-1]
            if ext not in ['zip', 'rar', '7z', 'tar', 'gz']:
                await update.message.reply_text("⚠️ صيغة غير مدعومة. المدعومة: ZIP, RAR, 7Z, TAR, GZ")
                return
            extract_dir, err = extract_archive(temp_path, ext)
            if err:
                await update.message.reply_text(f"❌ فشل فك الضغط: {err}")
                return
            # إرسال الملفات المستخرجة
            for root, _, files in os.walk(extract_dir):
                for f in files:
                    await update.message.reply_document(
                        document=open(os.path.join(root, f), 'rb'),
                        caption=f"📂 {f}"
                    )
            await update.message.reply_text("✅ تم فك الضغط بنجاح!")
            add_points(user_id, 5, "فك ضغط")
            shutil.rmtree(extract_dir)
            os.remove(temp_path)
        
        elif mode == 'compress':
            await update.message.reply_text("⚠️ هذه الخدمة قيد التطوير.")
        
        elif mode == 'check_integrity':
            await update.message.reply_text("⚠️ هذه الخدمة قيد التطوير.")
        
        elif mode == 'analyze_libs':
            await update.message.reply_text("⚠️ هذه الخدمة قيد التطوير.")
        
        else:
            await update.message.reply_text("⚠️ نوع الملف غير مناسب للخدمة المختارة.")
    
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {str(e)}")
    
    context.user_data['mode'] = None

# ============================================
# 9. تشغيل البوت
# ============================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username and user.username.lower() == DEV_USERNAME.lower():
        keyboard = [
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
            [InlineKeyboardButton("📢 إرسال إذاعة", callback_data="admin_broadcast")],
            [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="admin_settings")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "👑 **لوحة التحكم**\n\nاختر الإجراء:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ هذا الأمر للمطور فقط.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_msg = (
        "📚 **قائمة الأوامر**\n\n"
        "/start - بدء البوت\n"
        "/help - عرض المساعدة\n"
        "/id - عرض معرفك\n"
        "/points - عرض نقاطك\n"
        "/referral - رابط الإحالة\n"
        "/admin - لوحة التحكم (للمطور)\n"
        "/stats - إحصائيات (للمطور)"
    )
    await update.message.reply_text(help_msg, parse_mode="Markdown")

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🆔 **معرفك**: `{user.id}`\n"
        f"👤 **اسمك**: {user.first_name}\n"
        f"📛 **معرفك**: @{user.username or 'لا يوجد'}",
        parse_mode="Markdown"
    )

async def points_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    await update.message.reply_text(
        f"💰 **رصيدك**: {user_data['points']} ريال",
        parse_mode="Markdown"
    )

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"
    await update.message.reply_text(
        f"🔗 **رابط الإحالة**\n\n`{link}`\n\n⭐ ستحصل على 10 ريال لكل مدعو!",
        parse_mode="Markdown"
    )

def main():
    init_db()
    
    request = HTTPXRequest(connect_timeout=30.0, read_timeout=60.0)
    app = Application.builder().token(TOKEN).request(request).build()
    
    # الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("points", points_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("admin", admin_panel))
    
    # معالجات
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    
    logger.info(f"🚀 {BOT_NAME} يعمل...")
    logger.info(f"👨‍💻 المطور: @{DEV_USERNAME}")
    logger.info(f"📢 القناة: {DEV_CHANNEL}")
    
    app.run_polling()

if __name__ == "__main__":
    main()
