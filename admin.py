from telebot import types
from premium_emojis import PREMIUM_EMOJI_IDS, BUTTON_STYLES
import json
import time

class AdminPanel:
    def __init__(self, bot, db, admin_ids):
        self.bot = bot
        self.db = db
        self.admin_ids = admin_ids
    
    def is_admin(self, user_id):
        return user_id in self.admin_ids
    
    def get_premium_emoji(self, emoji):
        return PREMIUM_EMOJI_IDS.get(emoji, emoji)
    
    def create_admin_keyboard(self):
        """Create inline keyboard with premium emojis and styles"""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # Row 1: Stats & Broadcast
        btn1 = types.InlineKeyboardButton(
            f"{self.get_premium_emoji('📊')} Stats", 
            callback_data="admin_stats"
        )
        btn2 = types.InlineKeyboardButton(
            f"{self.get_premium_emoji('📢')} Broadcast", 
            callback_data="admin_broadcast"
        )
        keyboard.add(btn1, btn2)
        
        # Row 2: Ban & Unban
        btn3 = types.InlineKeyboardButton(
            f"{self.get_premium_emoji('🚫')} Ban User",
            callback_data="admin_ban"
        )
        btn4 = types.InlineKeyboardButton(
            f"{self.get_premium_emoji('✅')} Unban User",
            callback_data="admin_unban"
        )
        keyboard.add(btn3, btn4)
        
        # Row 3: Set Rate & Footer
        btn5 = types.InlineKeyboardButton(
            f"{self.get_premium_emoji('💰')} Set Rate",
            callback_data="admin_setrate"
        )
        btn6 = types.InlineKeyboardButton(
            f"{self.get_premium_emoji('📝')} Set Footer",
            callback_data="admin_setfooter"
        )
        keyboard.add(btn5, btn6)
        
        # Row 4: Logs & Refresh
        btn7 = types.InlineKeyboardButton(
            f"{self.get_premium_emoji('📋')} Logs",
            callback_data="admin_logs"
        )
        btn8 = types.InlineKeyboardButton(
            f"{self.get_premium_emoji('🔄')} Refresh",
            callback_data="admin_refresh"
        )
        keyboard.add(btn7, btn8)
        
        # Row 5: Close
        btn9 = types.InlineKeyboardButton(
            f"{self.get_premium_emoji('❌')} Close",
            callback_data="admin_close"
        )
        keyboard.add(btn9)
        
        return keyboard
    
    def admin_dashboard(self, message):
        if not self.is_admin(message.from_user.id):
            self.bot.reply_to(message, "❌ Access denied!")
            return
        
        user_count = self.db.get_user_count()
        active_users = self.db.get_active_users(24)
        
        text = f"""🔐 *Admin Dashboard*

{self.get_premium_emoji('👥')} *Total Users:* {user_count}
{self.get_premium_emoji('⚡')} *Active (24h):* {active_users}

{self.get_premium_emoji('⭐')} *Star Rate:* ₹{self.db.get_config('star_rate')}

{self.get_premium_emoji('📝')} *Footer:* 
{self.db.get_config('footer')[:50]}...

Select an option below:"""
        
        keyboard = self.create_admin_keyboard()
        self.bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode="Markdown")
    
    def handle_callback(self, call):
        if not self.is_admin(call.from_user.id):
            self.bot.answer_callback_query(call.id, "❌ Access denied!", show_alert=True)
            return
        
        data = call.data
        
        if data == "admin_stats":
            self.show_stats(call)
        elif data == "admin_broadcast":
            self.start_broadcast(call)
        elif data == "admin_ban":
            self.start_ban(call)
        elif data == "admin_unban":
            self.start_unban(call)
        elif data == "admin_setrate":
            self.start_setrate(call)
        elif data == "admin_setfooter":
            self.start_setfooter(call)
        elif data == "admin_logs":
            self.show_logs(call)
        elif data == "admin_refresh":
            self.refresh_prices(call)
        elif data == "admin_close":
            self.bot.delete_message(call.message.chat.id, call.message.message_id)
            self.bot.answer_callback_query(call.id, "Panel closed")
    
    def show_stats(self, call):
        user_count = self.db.get_user_count()
        active_24h = self.db.get_active_users(24)
        active_7d = self.db.get_active_users(168)
        
        text = f"""📊 *Statistics*

{self.get_premium_emoji('👥')} Total Users: {user_count}
{self.get_premium_emoji('⚡')} Active (24h): {active_24h}
{self.get_premium_emoji('📅')} Active (7d): {active_7d}
{self.get_premium_emoji('⭐')} Star Rate: ₹{self.db.get_config('star_rate')}"""
        
        self.bot.edit_message_text(
            text, 
            call.message.chat.id, 
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=self.create_admin_keyboard()
        )
        self.bot.answer_callback_query(call.id, "✅ Stats updated")
    
    def start_broadcast(self, call):
        self.bot.edit_message_text(
            f"📢 *Broadcast Mode*\n\n{self.get_premium_emoji('📝')} Send your broadcast message now.\n\nType /cancel to cancel.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
        self.bot.register_next_step_handler(call.message, self.process_broadcast)
        self.bot.answer_callback_query(call.id)
    
    def process_broadcast(self, message):
        if message.text == "/cancel":
            self.bot.reply_to(message, "❌ Broadcast cancelled")
            return
        
        users = self.db.get_all_users()
        success = 0
        failed = 0
        
        status_msg = self.bot.reply_to(message, f"⏳ Sending broadcast to {len(users)} users...")
        
        for user_id in users:
            try:
                self.bot.send_message(user_id[0], f"📢 *Broadcast*\n\n{message.text}", parse_mode="Markdown")
                success += 1
                time.sleep(0.1)  # Rate limit
            except:
                failed += 1
        
        self.bot.edit_message_text(
            f"✅ *Broadcast Complete*\n\n{self.get_premium_emoji('✅')} Sent: {success}\n{self.get_premium_emoji('❌')} Failed: {failed}",
            status_msg.chat.id,
            status_msg.message_id,
            parse_mode="Markdown"
        )
        
        self.db.add_log("INFO", f"Broadcast sent to {success} users")
    
    def start_ban(self, call):
        self.bot.edit_message_text(
            f"🚫 *Ban User*\n\n{self.get_premium_emoji('🆔')} Send user ID to ban:\n\nType /cancel to cancel.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
        self.bot.register_next_step_handler(call.message, self.process_ban)
        self.bot.answer_callback_query(call.id)
    
    def process_ban(self, message):
        if message.text == "/cancel":
            self.bot.reply_to(message, "❌ Cancelled")
            return
        
        try:
            user_id = int(message.text.strip())
            self.db.ban_user(user_id)
            self.bot.reply_to(message, f"✅ User {user_id} banned successfully")
            self.db.add_log("INFO", f"User {user_id} banned by admin")
        except:
            self.bot.reply_to(message, "❌ Invalid user ID")
    
    def start_unban(self, call):
        self.bot.edit_message_text(
            f"✅ *Unban User*\n\n{self.get_premium_emoji('🆔')} Send user ID to unban:\n\nType /cancel to cancel.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
        self.bot.register_next_step_handler(call.message, self.process_unban)
        self.bot.answer_callback_query(call.id)
    
    def process_unban(self, message):
        if message.text == "/cancel":
            self.bot.reply_to(message, "❌ Cancelled")
            return
        
        try:
            user_id = int(message.text.strip())
            self.db.unban_user(user_id)
            self.bot.reply_to(message, f"✅ User {user_id} unbanned successfully")
            self.db.add_log("INFO", f"User {user_id} unbanned by admin")
        except:
            self.bot.reply_to(message, "❌ Invalid user ID")
    
    def start_setrate(self, call):
        self.bot.edit_message_text(
            f"💰 *Set Star Rate*\n\n{self.get_premium_emoji('⭐')} Current rate: ₹{self.db.get_config('star_rate')}\n\nSend new rate (e.g., 1.5):\n\nType /cancel to cancel.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
        self.bot.register_next_step_handler(call.message, self.process_setrate)
        self.bot.answer_callback_query(call.id)
    
    def process_setrate(self, message):
        if message.text == "/cancel":
            self.bot.reply_to(message, "❌ Cancelled")
            return
        
        try:
            rate = float(message.text.strip())
            self.db.set_config('star_rate', str(rate))
            self.bot.reply_to(message, f"✅ Star rate updated to ₹{rate}")
            self.db.add_log("INFO", f"Star rate changed to ₹{rate}")
        except:
            self.bot.reply_to(message, "❌ Invalid rate. Please send a number (e.g., 1.5)")
    
    def start_setfooter(self, call):
        self.bot.edit_message_text(
            f"📝 *Set Footer*\n\n{self.get_premium_emoji('📝')} Current footer:\n{self.db.get_config('footer')}\n\nSend new footer text:\n\nType /cancel to cancel.",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
        self.bot.register_next_step_handler(call.message, self.process_setfooter)
        self.bot.answer_callback_query(call.id)
    
    def process_setfooter(self, message):
        if message.text == "/cancel":
            self.bot.reply_to(message, "❌ Cancelled")
            return
        
        footer = message.text.strip()
        self.db.set_config('footer', footer)
        self.bot.reply_to(message, f"✅ Footer updated successfully")
        self.db.add_log("INFO", "Footer updated")
    
    def show_logs(self, call):
        logs = self.db.get_logs(20)
        if not logs:
            text = "📋 *No logs found*"
        else:
            text = f"📋 *Recent Logs*\n\n{self.get_premium_emoji('🔄')} Last 20 entries:\n"
            for timestamp, level, msg in logs:
                time_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(timestamp))
                emoji = "ℹ️" if level == "INFO" else "⚠️"
                text += f"{emoji} `{time_str}` [{level}] {msg[:50]}\n"
        
        self.bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=self.create_admin_keyboard()
        )
        self.bot.answer_callback_query(call.id)
    
    def refresh_prices(self, call):
        self.bot.edit_message_text(
            f"🔄 *Refreshing prices...*\n\n{self.get_premium_emoji('⏳')} Please wait...",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
        
        try:
            # Import converter from main
            from bot import converter
            converter.get_live_prices()
            self.bot.edit_message_text(
                f"✅ *Prices Refreshed*\n\n{self.get_premium_emoji('✅')} Live prices updated successfully!",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=self.create_admin_keyboard()
            )
            self.db.add_log("INFO", "Prices refreshed manually")
        except Exception as e:
            self.bot.edit_message_text(
                f"❌ *Error refreshing prices*\n\n{self.get_premium_emoji('⚠️')} {str(e)}",
                call.message.chat.id,
                call.message.message_id,
                parse_mode="Markdown",
                reply_markup=self.create_admin_keyboard()
            )
            self.db.add_log("ERROR", f"Price refresh failed: {e}")
        
        self.bot.answer_callback_query(call.id)
