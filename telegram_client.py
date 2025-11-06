#Telegram
from telethon import TelegramClient, events
import config
import os
from data_manager import load_chat_ids, get_webhook
import requests

api_id = config.telegram_api_id
api_hash = config.telegram_api_hash

client = TelegramClient('session_test', api_id, api_hash)

os.makedirs("downloads", exist_ok=True)
chat_ids = []
url = []

async def reload_chat_ids():
    global chat_ids
    chat_ids = await load_chat_ids()
    # Update the event handler with new chat IDs
    client.remove_event_handler(new_message_handler)
    client.add_event_handler(new_message_handler, events.NewMessage(chats=chat_ids))

#On message in telegram
@client.on(events.NewMessage(chats=chat_ids))
async def new_message_handler(event):
    #Get sender info

    sender_chat = await event.get_chat()
    chat_name = sender_chat.title if sender_chat.title else sender_chat.id

    message_text = (f"New message from {chat_name}:\n{event.message.text}")
    file_path = None
    if event.message.media:
        file_path = await client.download_media(event.message, file="downloads/")

    url = get_webhook()
    for webhook_url in url:
        requests.post(webhook_url, data={"content": message_text}, files={"file": open(file_path, "rb")} if file_path else None)

    if file_path and os.path.exists(file_path):
        os.remove(file_path)

# Function to check if a channel is valid
async def is_valid_channel(channel_id):
    try:
        # Try to get the channel info
        channel = await client.get_entity(int(channel_id))
        return True, channel.title if hasattr(channel, 'title') else f"Chat {channel_id}"
    except Exception as e:
        return False, str(e)
    