#Telegram
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import ChannelInvalidError
import asyncio
import os
import json

api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")

client = TelegramClient('session_test', api_id, api_hash)

# Load chat IDs from a JSON file
def load_chat_ids():
    try:
        with open("channels.json", "r") as f:
            data = json.load(f)
            # Extract all unique chat IDs across all users
            all_chat_ids = []
            for user_id in data:
                all_chat_ids.extend(data[user_id]["id"])
            return list(set(all_chat_ids))  # Remove duplicates
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is invalid, create an empty structure
        with open("channels.json", "w") as f:
            json.dump({}, f)
        return []

chat_ids = load_chat_ids()

os.makedirs("downloads", exist_ok=True)

#Discord
import discord
from discord.ext import commands
from discord import app_commands, Webhook, SyncWebhook
from typing import Optional
import aiohttp


token = os.getenv("DISCORD_TOKEN")
intents = discord.Intents().all()
bot = commands.Bot(command_prefix="!!", intents=intents)
url = os.getenv("DISCORD_WEBHOOK_URL")
file_path = "channels.json"
MY_GUILD = discord.Object(id=1094865217139257405)

webhook = SyncWebhook.from_url(url)
@bot.event
async def on_ready():
    print("Logged in as {0.user}".format(bot))

@bot.tree.command(name="hello", description="Say hello", guild=MY_GUILD)
async def sayHello(interaction: discord.Interaction):
    await interaction.response.send_message("Hello there")

#Sync slash commands
@bot.command(name='sync', description='Owner only')
async def sync(ctx):
    if ctx.author.id == 726121153034190879:
        await bot.tree.sync()
        await ctx.send('Command tree synced.')
    else:
        await ctx.send('You must be the owner to use this command!')

#Send scrapped message to discord
async def send_to_discord(message):
    # channel = bot.get_channel(1338755255139176583)
    # await channel.send(message)
    webhook.send(message)

#On message in telegram
@client.on(events.NewMessage(chats=chat_ids))
async def new_message_handler(event):
    #Get sender info
    sender_chat = await event.get_chat()
    chat_name = sender_chat.title if sender_chat.title else sender_chat.id

    if event.message.text:
        message_text = (f"New message from {chat_name}: {event.message.text}")
        print(message_text)
        await send_to_discord(message_text) #discord bot
    
    if event.message.media:
        file_path = await client.download_media(event.message, file="downloads/")
        message_text = (f"Pic from {chat_name} {file_path}")
        await send_to_discord(message_text)

# Function to check if a channel is valid
async def is_valid_channel(channel_id):
    try:
        # Try to get the channel info
        channel = await client.get_entity(int(channel_id))
        return True, channel.title if hasattr(channel, 'title') else f"Chat {channel_id}"
    except Exception as e:
        return False, str(e)

# Function to reload chat IDs after changes
async def reload_chat_ids():
    global chat_ids
    chat_ids = load_chat_ids()
    # Update the event handler with new chat IDs
    client.remove_event_handler(new_message_handler)
    client.add_event_handler(new_message_handler, events.NewMessage(chats=chat_ids))
    print(f"Reloaded chat IDs: {chat_ids}")

async def main():
    print("Started")
    await reload_chat_ids()  # Initial load
    await bot.start(token)

# Adding new tg channel by ID
@bot.tree.command(name="addchannel", description="Add a Telegram channel by ID")
@app_commands.describe(channel_id="Telegram channel ID")
async def addchannel(interaction: discord.Interaction, channel_id: str):
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Convert to integer
        channel_id_int = int(channel_id)
        
        # Check if channel is valid
        is_valid, channel_name = await is_valid_channel(channel_id_int)
        if not is_valid:
            await interaction.followup.send(f"Invalid channel ID: {channel_name}", ephemeral=True)
            return
        
        # Load existing data
        try:
            with open(file_path, "r") as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        
        # Add user if not exists
        user_id = str(interaction.user.id)
        if user_id not in data:
            data[user_id] = {"id": []}
        
        # Add channel if not already in list
        if channel_id_int not in data[user_id]["id"]:
            data[user_id]["id"].append(channel_id_int)
            
            # Save updated data
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
                
            # Reload chat IDs
            await reload_chat_ids()
            
            await interaction.followup.send(f"Added channel: {channel_name} ({channel_id_int})", ephemeral=True)
        else:
            await interaction.followup.send("This channel is already in your list", ephemeral=True)
    except ValueError:
        await interaction.followup.send("Please provide a valid numerical ID", ephemeral=True)

# Adding new tg channel by URL
@bot.tree.command(name="addtg", description="Add a TG dm or group to the forwarder")
@app_commands.describe(url="URL of group or dms (Find by using TG web)")
async def addtg(interaction: discord.Interaction, url: str):
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Parse channel ID from URL
        if url.startswith("https://web.telegram.org/a/#-"):
            tg_id = int(url.removeprefix("https://web.telegram.org/a/#-"))
        elif url.startswith("https://web.telegram.org/a/#"):
            tg_id = int(url.removeprefix("https://web.telegram.org/a/#"))
        elif url.startswith("https://t.me/"):
            # For public channel links, try to get the entity
            channel_username = url.removeprefix("https://t.me/")
            try:
                channel = await client.get_entity(channel_username)
                tg_id = channel.id
            except Exception as e:
                await interaction.followup.send(f"Failed to resolve channel from link: {str(e)}", ephemeral=True)
                return
        else:
            await interaction.followup.send("Invalid URL format. Use web.telegram.org or t.me links.", ephemeral=True)
            return
        
        # Check if channel is valid
        is_valid, channel_name = await is_valid_channel(tg_id)
        if not is_valid:
            await interaction.followup.send(f"Invalid channel: {channel_name}", ephemeral=True)
            return
        
        # Load existing data
        try:
            with open(file_path, "r") as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        
        # Add user if not exists
        user_id = str(interaction.user.id)
        if user_id not in data:
            data[user_id] = {"id": []}
        
        # Add channel if not already in list
        if tg_id not in data[user_id]["id"]:
            data[user_id]["id"].append(tg_id)
            
            # Save updated data
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
                
            # Reload chat IDs
            await reload_chat_ids()
            
            await interaction.followup.send(f"Added channel: {channel_name} ({tg_id})", ephemeral=True)
        else:
            await interaction.followup.send("This channel is already in your list", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Error adding channel: {str(e)}", ephemeral=True)

# List channels
@bot.tree.command(name="listchannels", description="List all your Telegram channels and verify them")
async def listchannels(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    # Load existing data
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        await interaction.followup.send("No channels found. Add some channels first.", ephemeral=True)
        return
    
    user_id = str(interaction.user.id)
    if user_id not in data or not data[user_id]["id"]:
        await interaction.followup.send("You don't have any channels in your list.", ephemeral=True)
        return
    
    # Verify and list all channels
    channels_list = []
    for index, channel_id in enumerate(data[user_id]["id"]):
        is_valid, channel_name = await is_valid_channel(channel_id)
        status = "✅ Valid" if is_valid else "❌ Invalid"
        channels_list.append(f"{index+1}. {channel_name} (ID: {channel_id}) - {status}")
    
    response = "Your Telegram Channels:\n" + "\n".join(channels_list)
    await interaction.followup.send(response, ephemeral=True)

# Delete a channel
@bot.tree.command(name="deletechannel", description="Delete a Telegram channel from your list")
@app_commands.describe(channel_id="Telegram channel ID to delete")
async def deletechannel(interaction: discord.Interaction, channel_id: str):
    await interaction.response.defer(ephemeral=True)
    
    try:
        channel_id_int = int(channel_id)
        
        # Load existing data
        try:
            with open(file_path, "r") as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            await interaction.followup.send("No channels found to delete.", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        if user_id not in data or not data[user_id]["id"]:
            await interaction.followup.send("You don't have any channels in your list.", ephemeral=True)
            return
        
        # Check if channel exists in user's list
        if channel_id_int not in data[user_id]["id"]:
            await interaction.followup.send("This channel is not in your list.", ephemeral=True)
            return
        
        # Get channel name before deletion for confirmation
        is_valid, channel_name = await is_valid_channel(channel_id_int)
        channel_display = channel_name if is_valid else f"Channel {channel_id_int}"
        
        # Remove channel
        data[user_id]["id"].remove(channel_id_int)
        
        # Save updated data
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
            
        # Reload chat IDs
        await reload_chat_ids()
        
        await interaction.followup.send(f"Deleted {channel_display} from your list.", ephemeral=True)
    except ValueError:
        await interaction.followup.send("Please provide a valid numerical ID", ephemeral=True)

# Delete a channel by index number
@bot.tree.command(name="deletechannel_index", description="Delete a Telegram channel by its list number")
@app_commands.describe(index="Channel number from the list (use /listchannels first)")
async def deletechannel_index(interaction: discord.Interaction, index: int):
    await interaction.response.defer(ephemeral=True)
    
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        await interaction.followup.send("No channels found to delete.", ephemeral=True)
        return
    
    user_id = str(interaction.user.id)
    if user_id not in data or not data[user_id]["id"]:
        await interaction.followup.send("You don't have any channels in your list.", ephemeral=True)
        return
    
    # Check if index is valid
    if index < 1 or index > len(data[user_id]["id"]):
        await interaction.followup.send(f"Invalid index. Please choose a number between 1 and {len(data[user_id]['id'])}.", ephemeral=True)
        return
    

    channel_id = data[user_id]["id"][index-1]
    
    # Get channel name before deletion for confirmation
    is_valid, channel_name = await is_valid_channel(channel_id)
    channel_display = channel_name if is_valid else f"Channel {channel_id}"
    
    data[user_id]["id"].pop(index-1)
    
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
        
    # Reload chat IDs
    await reload_chat_ids()
    
    await interaction.followup.send(f"Deleted {channel_display} (index {index}) from your list.", ephemeral=True)

with client:
    client.loop.run_until_complete(main())
    client.run_until_disconnected()
