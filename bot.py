import os
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import requests
import re
import time
import logging
import telebot
from telebot import types

from config import Config
from database import Database
from admin import AdminPanel
from premium_emojis import PREMIUM_EMOJI_IDS

# ============= LOGGING =============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============= DATABASE =============
db = Database(Config.DATABASE_FILE)

# ============= CONVERTER CLASS =============
class CryptoConverter:
    def __init__(self):
        self.prices = {}
        self.last_update = 0
        self.cache_duration = Config.CACHE_DURATION
        self.usd_to_inr = 0
        self.star_rate_usd = 0
    
    def get_live_prices(self):
        current_time = time.time()
        
        if self.prices and (current_time - self.last_update) < self.cache_duration:
            return self.prices
        
        try:
            logger.info("Fetching live prices...")
            
            # CoinGecko API - TON Price
            crypto_url = Config.COINGECKO_URL
            params = {'ids': 'the-open-network,tether', 'vs_currencies': 'usd'}
            response = requests.get(crypto_url, params=params, timeout=10)
            crypto_data = response.json()
            ton_price = crypto_data.get('the-open-network', {}).get('usd', 0)
            
            # ExchangeRate API - USD to INR
            inr_url = Config.EXCHANGE_RATE_URL
            inr_response = requests.get(inr_url, timeout=10)
            inr_data = inr_response.json()
            self.usd_to_inr = inr_data.get('rates', {}).get('INR', 0)
            
            # Calculate Star rate in USD
            star_rate = float(db.get_config('star_rate') or Config.STAR_RATE_INR)
            if self.usd_to_inr > 0:
                self.star_rate_usd = star_rate / self.usd_to_inr
            else:
                self.star_rate_usd = 0.01349
            
            self.prices = {
                'TON': ton_price,
                'USDT': 1.0,
                'INR': 1 / self.usd_to_inr if self.usd_to_inr > 0 else 0,
                'STAR': self.star_rate_usd
            }
            
            self.last_update = current_time
            
            logger.info(f"USD to INR: ₹{self.usd_to_inr}")
            logger.info(f"1 Star = ₹{star_rate} = ${self.star_rate_usd:.6f}")
            logger.info(f"Prices: {self.prices}")
            
            return self.prices
            
        except Exception as e:
            logger.error(f"API Error: {e}")
            db.add_log("ERROR", f"API Error: {e}")
            if self.prices:
                return self.prices
            raise Exception("API failed")
    
    def get_all_conversions(self, amount, currency):
        prices = self.get_live_prices()
        currency = currency.upper()
        
        logger.info(f"Converting: {amount} {currency}")
        
        # Step 1: Convert to USD first
        if currency == 'TON':
            usd_value = amount * prices['TON']
        elif currency == 'USDT':
            usd_value = amount * prices['USDT']
        elif currency == 'INR':
            usd_value = amount * prices['INR']
        elif currency == 'STAR':
            usd_value = amount * prices['STAR']
        else:
            usd_value = amount
        
        logger.info(f"USD Value: ${usd_value:.6f}")
        
        # Step 2: Convert USD to all currencies
        results = {}
        
        if prices['TON'] > 0:
            results['TON'] = usd_value / prices['TON']
        else:
            results['TON'] = 0
        
        if prices['USDT'] > 0:
            results['USDT'] = usd_value / prices['USDT']
        else:
            results['USDT'] = 0
        
        if prices['INR'] > 0:
            results['INR'] = usd_value / prices['INR']
        else:
            results['INR'] = 0
        
        if self.usd_to_inr > 0:
            inr_value = usd_value * self.usd_to_inr
            star_rate = float(db.get_config('star_rate') or Config.STAR_RATE_INR)
            results['STAR'] = inr_value / star_rate
        else:
            results['STAR'] = 0
        
        logger.info(f"Results: {results}")
        return results

converter = CryptoConverter()

# ============= BOT =============
bot = telebot.TeleBot(Config.BOT_TOKEN)
admin_panel = AdminPanel(bot, db, Config.ADMIN_IDS)

def get_premium_emoji(emoji):
    return PREMIUM_EMOJI_IDS.get(emoji, emoji)

def parse_input(text):
    text = text.lower().strip()
    logger.info(f"Parsing: {text}")
    
    # TON - t, ton
    match = re.match(r'^(\d+(?:\.\d+)?)\s*(?:ton|t)$', text)
    if match:
        return float(match.group(1)), 'TON'
    
    # USDT - u, usdt
    match = re.match(r'^(\d+(?:\.\d+)?)\s*(?:usdt|u)$', text)
    if match:
        return float(match.group(1)), 'USDT'
    
    # INR - i, inr, ₹
    match = re.match(r'^(\d+(?:\.\d+)?)\s*(?:inr|i)$', text)
    if match:
        return float(match.group(1)), 'INR'
    
    match = re.match(r'^₹\s*(\d+(?:\.\d+)?)$', text)
    if match:
        return float(match.group(1)), 'INR'
    
    match = re.match(r'^(\d+(?:\.\d+)?)\s*₹$', text)
    if match:
        return float(match.group(1)), 'INR'
    
    # STARS - s, star, stars, ⭐
    match = re.match(r'^(\d+(?:\.\d+)?)\s*(?:star|stars|s)$', text)
    if match:
        return float(match.group(1)), 'STAR'
    
    match = re.match(r'^⭐\s*(\d+(?:\.\d+)?)$', text)
    if match:
        return float(match.group(1)), 'STAR'
    
    match = re.match(r'^(\d+(?:\.\d+)?)\s*⭐$', text)
    if match:
        return float(match.group(1)), 'STAR'
    
    return None, None

def is_valid_input(text):
    text = text.lower().strip()
    
    valid_patterns = [
        r'^\d+(?:\.\d+)?\s*ton$',
        r'^\d+(?:\.\d+)?\s*t$',
        r'^\d+(?:\.\d+)?\s*usdt$',
        r'^\d+(?:\.\d+)?\s*u$',
        r'^\d+(?:\.\d+)?\s*inr$',
        r'^\d+(?:\.\d+)?\s*i$',
        r'^₹\s*\d+(?:\.\d+)?$',
        r'^\d+(?:\.\d+)?\s*₹$',
        r'^\d+(?:\.\d+)?\s*star$',
        r'^\d+(?:\.\d+)?\s*stars$',
        r'^\d+(?:\.\d+)?\s*s$',
        r'^⭐\s*\d+(?:\.\d+)?$',
        r'^\d+(?:\.\d+)?\s*⭐$',
    ]
    
    for pattern in valid_patterns:
        if re.match(pattern, text):
            return True
    return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Track user
    db.add_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    star_rate = db.get_config('star_rate') or Config.STAR_RATE_INR
    
    welcome_text = f"""🔄 *Crypto Converter Bot*

{get_premium_emoji('💎')} Convert between TON, USDT, INR, and Telegram Stars!

*How to use:*
• 2ton or 2t - 2 TON
• 5usdt or 5u - 5 USDT
• 500inr or 500i - 500 INR
• 100star or 100s - 100 Stars

*Examples:*
1t  2ton  5u  100usdt  500i  250s

{get_premium_emoji('⭐')} 1 Star = ₹{star_rate}

Use /help for more info."""
    
    # Create inline keyboard with premium emojis
    keyboard = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton(
        f"{get_premium_emoji('📊')} Status",
        callback_data="check_status"
    )
    btn2 = types.InlineKeyboardButton(
        f"{get_premium_emoji('💡')} Help",
        callback_data="show_help"
    )
    keyboard.add(btn1, btn2)
    
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=keyboard)

@bot.message_handler(commands=['help'])
def send_help(message):
    db.add_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    star_rate = db.get_config('star_rate') or Config.STAR_RATE_INR
    
    help_text = f"""📚 *Help & Commands*

{get_premium_emoji('🔢')} *Supported Formats:*
TON: 1t, 2ton
USDT: 5u, 10usdt
INR: 500i, ₹500, 500₹
Stars: 100⭐, 250s, 500star

{get_premium_emoji('📋')} *Commands:*
/start - Welcome
/help - This help
/status - Check prices
/admin - Admin panel

{get_premium_emoji('⭐')} Star Rate: 1 Star = ₹{star_rate}

*Example:*
2ton → Shows all conversions"""
    
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['status'])
def send_status(message):
    try:
        prices = converter.get_live_prices()
        usd_to_inr = converter.usd_to_inr
        star_rate = db.get_config('star_rate') or Config.STAR_RATE_INR
        
        status_text = f"""✅ *Bot Status*

🟢 Online

*Current Prices:*
{get_premium_emoji('💎')} TON: ${prices.get('TON', 0):.4f}
{get_premium_emoji('💵')} USDT: ${prices.get('USDT', 0):.4f}
{get_premium_emoji('🇮🇳')} USD to INR: ₹{usd_to_inr:.2f}
{get_premium_emoji('⭐')} Stars: ₹{star_rate:.2f} each
{get_premium_emoji('⭐')} Stars: ${prices.get('STAR', 0):.6f} each

⚡ 1 Star = ₹{star_rate}"""
        
        bot.reply_to(message, status_text, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['admin'])
def admin_command(message):
    admin_panel.admin_dashboard(message)

@bot.message_handler(func=lambda message: True)
def handle_conversion(message):
    try:
        if message.text.startswith('/'):
            return
        
        # Check if user is banned
        user = db.get_user(message.from_user.id)
        if user and user[6] == 1:  # banned column
            bot.reply_to(message, "🚫 You are banned from using this bot!")
            return
        
        text = message.text.strip()
        
        if not is_valid_input(text):
            logger.info(f"Ignoring invalid input: {text}")
            return
        
        amount, currency = parse_input(text)
        
        if amount is None or currency is None:
            logger.info(f"Ignoring invalid input (parse failed): {text}")
            return
        
        # Track user
        db.add_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        )
        
        bot.send_chat_action(message.chat.id, 'typing')
        
        conversions = converter.get_all_conversions(amount, currency)
        star_rate = db.get_config('star_rate') or Config.STAR_RATE_INR
        footer = db.get_config('footer') or "━━━━━━━━━━━━━━━━━━\nMade by @cyber_amit"
        
        # Track conversion
        db.add_conversion(message.from_user.id, amount, currency)
        
        result = f"💎 *TON* : {conversions.get('TON', 0):.4f}\n"
        result += f"💵 *USDT* : {conversions.get('USDT', 0):.4f}\n"
        result += f"🇮🇳 *INR* : {conversions.get('INR', 0):.2f}\n"
        result += f"⭐ *STARS* : {conversions.get('STAR', 0):.2f}\n"
        result += f"\n📊 {amount} {currency} → All Currencies"
        result += f"\n⭐ 1 Star = ₹{star_rate}"
        result += f"\n{footer}"
        
        bot.reply_to(message, result, parse_mode="Markdown")
        logger.info(f"Conversion sent: {amount} {currency} → {conversions}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        db.add_log("ERROR", f"Conversion error: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "check_status":
        try:
            prices = converter.get_live_prices()
            usd_to_inr = converter.usd_to_inr
            star_rate = db.get_config('star_rate') or Config.STAR_RATE_INR
            
            status_text = f"""✅ *Live Prices*

{get_premium_emoji('💎')} TON: ${prices.get('TON', 0):.4f}
{get_premium_emoji('💵')} USDT: ${prices.get('USDT', 0):.4f}
{get_premium_emoji('🇮🇳')} USD to INR: ₹{usd_to_inr:.2f}
{get_premium_emoji('⭐')} Stars: ₹{star_rate:.2f}

⚡ 1 Star = ₹{star_rate}"""
            
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, status_text, parse_mode="Markdown")
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ Error: {str(e)}", show_alert=True)
    
    elif call.data == "show_help":
        star_rate = db.get_config('star_rate') or Config.STAR_RATE_INR
        
        help_text = f"""📚 *Quick Help*

{get_premium_emoji('🔢')} *Formats:*
TON: 1t, 2ton
USDT: 5u, 10usdt
INR: 500i, ₹500
Stars: 100⭐, 250s

⭐ 1 Star = ₹{star_rate}

Use /help for full commands"""
        
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, help_text, parse_mode="Markdown")
    
    else:
        # Handle admin callbacks
        admin_panel.handle_callback(call)

def main():
    try:
        print("=" * 50)
        print("🤖 Crypto Converter Bot Starting...")
        print("=" * 50)
        
        # Test database
        user_count = db.get_user_count()
        print(f"📊 Database: {user_count} users")
        print(f"👑 Admin IDs: {Config.ADMIN_IDS}")
        
        # Test API
        try:
            prices = converter.get_live_prices()
            usd_to_inr = converter.usd_to_inr
            star_rate = db.get_config('star_rate') or Config.STAR_RATE_INR
            star_in_usd = converter.star_rate_usd
            
            print("✅ API Connected!")
            print(f"💎 TON: ${prices.get('TON', 0):.4f}")
            print(f"💵 USDT: ${prices.get('USDT', 0):.4f}")
            print(f"🇮🇳 USD to INR: ₹{usd_to_inr:.2f}")
            print(f"⭐ 1 Star = ₹{star_rate} = ${star_in_usd:.6f}")
        except Exception as e:
            print(f"⚠️ API Warning: {e}")
        
        print("\n" + "=" * 50)
        print("✅ Bot is running...")
        print("Press Ctrl+C to stop")
        print("=" * 50 + "\n")
        
        bot.infinity_polling()
        
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
