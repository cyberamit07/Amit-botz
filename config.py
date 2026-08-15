import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bot Token
    BOT_TOKEN = os.environ.get('BOT_TOKEN', "8721462024:AAENleXPiWyrSB5C_23CzZOxzSkwTBFF8Hc")
    
    # Admin IDs - Owner ko add kiya
    ADMIN_IDS = [8603893462]  # ✅ Owner ID set
    
    # Star Rate (1 Star = ₹1.3)
    STAR_RATE_INR = float(os.environ.get('STAR_RATE_INR', '1.3'))
    
    # Database
    DATABASE_FILE = os.environ.get('DATABASE_FILE', 'bot.db')
    
    # API Endpoints
    COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGE_RATE_URL = "https://api.exchangerate-api.com/v4/latest/USD"
    
    # Cache Duration (seconds)
    CACHE_DURATION = int(os.environ.get('CACHE_DURATION', '60'))
