#Telegram
import config
from telegram_client import client, reload_chat_ids
from discord_bot import bot, token

api_id = config.telegram_api_id
api_hash = config.telegram_api_hash

async def main():
    print("Started")
    await reload_chat_ids()  # Initial load
    await bot.start(token)

with client:
    client.loop.run_until_complete(main())
    client.run_until_disconnected()