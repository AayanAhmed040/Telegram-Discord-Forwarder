import os
from dotenv import load_dotenv
load_dotenv()

#Telegram API credentials
telegram_api_id = os.getenv("TELEGRAM_API_ID")
telegram_api_hash = os.getenv("TELEGRAM_API_HASH")

#Discord credentials
discord_token = os.getenv("DISCORD_TOKEN")