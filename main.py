#Telegram
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.errors import ChannelInvalidError
import asyncio
import os
import json
from dotenv import load_dotenv
load_dotenv()


api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")

client = TelegramClient('session_test', api_id, api_hash)

# Function to load user data
def load_user_data():
    try:
        with open("user_data.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Create default structure if file doesn't exist
        default_data = {"users": {}, "paying_users": []}
        with open("user_data.json", "w") as f:
            json.dump(default_data, f, indent=2)
        return default_data

# Load chat IDs from user data
def load_chat_ids():
    user_data = load_user_data()
    all_chat_ids = []
    
    for user_id, user_info in user_data["users"].items():
        # Add channel forwarding info
        if "channels" in user_info:
            for channel_info in user_info["channels"]:
                all_chat_ids.append((channel_info["id"], user_id))
                
    return all_chat_ids

# Define constants
FREE_TIER_LIMIT = 2
OWNER_ID = 726121153034190879

os.makedirs("downloads", exist_ok=True)

#Discord
import discord
from discord.ext import commands
from discord import app_commands, Webhook
from typing import Optional
import aiohttp

token = os.getenv("DISCORD_BOT_TOKEN")
intents = discord.Intents().all()
bot = commands.Bot(command_prefix="!!", intents=intents)
url = os.getenv("DISCORD_WEBHOOK_URL")
user_data_path = "user_data.json"

# Channel ID to user ID mapping for message forwarding
channel_to_user_map = {}

# User destination channels
user_destination_channels = {}

@bot.event
async def on_ready():
    print("Logged in as {0.user}".format(bot))
    # Initial loading of chat IDs and setting up message handlers
    await reload_chat_ids()

# Sync slash commands to all guilds the bot is in
@bot.command(name='sync', description='Owner only')
async def sync(ctx):
    if ctx.author.id == OWNER_ID:
        # Sync to current guild
        await bot.tree.sync(guild=ctx.guild)
        # Sync globally
        await bot.tree.sync()
        await ctx.send('Command tree synced globally and to this server.')
    else:
        await ctx.send('You must be the owner to use this command!')

# Check if user is the owner of the bot
def is_owner(user_id):
    return user_id == OWNER_ID

# Check if user is a paying subscriber
def is_paying_user(user_id):
    user_data = load_user_data()
    return str(user_id) in user_data["paying_users"]

# Get number of channels a user can have
def get_channel_limit(user_id):
    if is_owner(user_id) or is_paying_user(user_id):
        return float('inf')  # Unlimited
    return FREE_TIER_LIMIT

# Count how many channels a user currently has
def get_user_channel_count(user_id):
    user_data = load_user_data()
    user_id_str = str(user_id)
    
    if user_id_str in user_data["users"] and "channels" in user_data["users"][user_id_str]:
        return len(user_data["users"][user_id_str]["channels"])
    return 0

# Function to check if a channel is valid
async def is_valid_channel(channel_id):
    try:
        # Try to get the channel info
        channel = await client.get_entity(int(channel_id))
        return True, channel.title if hasattr(channel, 'title') else f"Chat {channel_id}"
    except Exception as e:
        return False, str(e)

# Set up event handlers for Telegram messages
async def setup_telegram_handlers():
    global channel_to_user_map
    
    # Clear existing event handlers
    client.remove_event_handler(new_message_handler)
    
    # Set up the mapping of channel IDs to user IDs
    chat_ids_with_users = load_chat_ids()
    channel_to_user_map = {channel_id: user_id for channel_id, user_id in chat_ids_with_users}
    
    # Get just the channel IDs for the event handler
    chat_ids = [channel_id for channel_id, _ in chat_ids_with_users]
    
    # Register the event handler with all channels
    if chat_ids:
        client.add_event_handler(new_message_handler, events.NewMessage(chats=chat_ids))
    
    # Load user destination channels
    user_data = load_user_data()
    for user_id, user_info in user_data["users"].items():
        if "destination_channel" in user_info:
            user_destination_channels[user_id] = user_info["destination_channel"]
    
    print(f"Set up handlers for {len(chat_ids)} channels")
    print(f"Channel to user mapping: {channel_to_user_map}")
    print(f"User destination channels: {user_destination_channels}")

# Function to reload chat IDs after changes
async def reload_chat_ids():
    await setup_telegram_handlers()

# On message in telegram
async def new_message_handler(event):
    try:
        # Get the channel ID that received the message
        channel_id = event.chat_id
        
        # Find which user this channel belongs to
        if channel_id in channel_to_user_map:
            user_id = channel_to_user_map[channel_id]
            
            # Get the destination channel for this user
            if user_id in user_destination_channels:
                destination_channel_id = user_destination_channels[user_id]
                destination_channel = bot.get_channel(destination_channel_id)
                
                if destination_channel:
                    # Get sender info
                    sender_chat = await event.get_chat()
                    chat_name = sender_chat.title if hasattr(sender_chat, 'title') else f"Chat {sender_chat.id}"
                    
                    if event.message.text:
                        message_text = f"New message from {chat_name}: {event.message.text}"
                        await destination_channel.send(message_text)
                    
                    if event.message.media:
                        file_path = await client.download_media(event.message, file="downloads/")
                        message_text = f"Pic from {chat_name} {file_path}"
                        await destination_channel.send(message_text)
                        # Send the actual file
                        if os.path.exists(file_path):
                            await destination_channel.send(file=discord.File(file_path))
                else:
                    print(f"Could not find destination channel {destination_channel_id} for user {user_id}")
            else:
                print(f"No destination channel set for user {user_id}")
        else:
            print(f"Channel {channel_id} not found in mapping")
            
    except Exception as e:
        print(f"Error handling Telegram message: {str(e)}")

# Command group for user management
@bot.tree.command(name="admin_add_paying", description="[ADMIN] Add a user to paying tier")
@app_commands.describe(user="The user to add to paying tier")
async def admin_add_paying(interaction: discord.Interaction, user: discord.Member):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    user_data = load_user_data()
    user_id_str = str(user.id)
    
    if user_id_str not in user_data["paying_users"]:
        user_data["paying_users"].append(user_id_str)
        
        with open(user_data_path, "w") as f:
            json.dump(user_data, f, indent=2)
        
        await interaction.followup.send(f"Added {user.display_name} to paying users.", ephemeral=True)
    else:
        await interaction.followup.send(f"{user.display_name} is already a paying user.", ephemeral=True)

@bot.tree.command(name="admin_remove_paying", description="[ADMIN] Remove a user from paying tier")
@app_commands.describe(user="The user to remove from paying tier")
async def admin_remove_paying(interaction: discord.Interaction, user: discord.Member):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    user_data = load_user_data()
    user_id_str = str(user.id)
    
    if user_id_str in user_data["paying_users"]:
        user_data["paying_users"].remove(user_id_str)
        
        with open(user_data_path, "w") as f:
            json.dump(user_data, f, indent=2)
        
        await interaction.followup.send(f"Removed {user.display_name} from paying users.", ephemeral=True)
    else:
        await interaction.followup.send(f"{user.display_name} is not a paying user.", ephemeral=True)

@bot.tree.command(name="admin_list_users", description="[ADMIN] List all users and their status")
async def admin_list_users(interaction: discord.Interaction):
    if not is_owner(interaction.user.id):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    user_data = load_user_data()
    
    # Prepare the message
    message = "**User Status**\n\n"
    message += "**Paying Users:**\n"
    
    if user_data["paying_users"]:
        for user_id in user_data["paying_users"]:
            try:
                user = await bot.fetch_user(int(user_id))
                channel_count = get_user_channel_count(user_id)
                message += f"- {user.name} (ID: {user_id}) - {channel_count} channels\n"
            except:
                message += f"- Unknown User (ID: {user_id})\n"
    else:
        message += "- None\n"
    
    message += "\n**Free Users:**\n"
    
    free_users = [uid for uid in user_data["users"] if uid not in user_data["paying_users"]]
    if free_users:
        for user_id in free_users:
            try:
                user = await bot.fetch_user(int(user_id))
                channel_count = get_user_channel_count(user_id)
                message += f"- {user.name} (ID: {user_id}) - {channel_count}/{FREE_TIER_LIMIT} channels\n"
            except:
                message += f"- Unknown User (ID: {user_id})\n"
    else:
        message += "- None\n"
    
    await interaction.followup.send(message, ephemeral=True)

# Set destination channel
@bot.tree.command(name="set_destination", description="Set which Discord channel your Telegram messages should be sent to")
@app_commands.describe(channel="The Discord channel to forward Telegram messages to")
async def set_destination(interaction: discord.Interaction, channel: discord.TextChannel):
    await interaction.response.defer(ephemeral=True)
    
    # Check if user has permission to set the channel
    if not interaction.user.guild_permissions.manage_channels and not channel.permissions_for(interaction.user).send_messages:
        await interaction.followup.send("You don't have permission to use this channel as a destination.", ephemeral=True)
        return
    
    # Check if bot has permission to send messages to the channel
    if not channel.permissions_for(interaction.guild.me).send_messages:
        await interaction.followup.send("I don't have permission to send messages to that channel.", ephemeral=True)
        return
    
    user_data = load_user_data()
    user_id_str = str(interaction.user.id)
    
    # Initialize user data if not exists
    if user_id_str not in user_data["users"]:
        user_data["users"][user_id_str] = {}
    
    # Set destination channel
    user_data["users"][user_id_str]["destination_channel"] = channel.id
    user_destination_channels[user_id_str] = channel.id
    
    with open(user_data_path, "w") as f:
        json.dump(user_data, f, indent=2)
    
    await interaction.followup.send(f"Your Telegram messages will now be forwarded to {channel.mention}.", ephemeral=True)

# Adding new tg channel by ID
@bot.tree.command(name="addchannel", description="Add a Telegram channel by ID")
@app_commands.describe(channel_id="Telegram channel ID")
async def addchannel(interaction: discord.Interaction, channel_id: str):
    await interaction.response.defer(ephemeral=True)
    
    user_id_str = str(interaction.user.id)
    user_data = load_user_data()
    
    # Check if user has set a destination channel
    if user_id_str not in user_data["users"] or "destination_channel" not in user_data["users"][user_id_str]:
        await interaction.followup.send("You need to set a destination channel first using /set_destination", ephemeral=True)
        return
    
    # Check channel limit for non-paying users
    channel_count = get_user_channel_count(interaction.user.id)
    channel_limit = get_channel_limit(interaction.user.id)
    
    if channel_count >= channel_limit:
        await interaction.followup.send(f"You've reached your limit of {channel_limit} channels. Upgrade to premium for unlimited channels.", ephemeral=True)
        return
    
    try:
        # Convert to integer
        channel_id_int = int(channel_id)
        
        # Check if channel is valid
        is_valid, channel_name = await is_valid_channel(channel_id_int)
        if not is_valid:
            await interaction.followup.send(f"Invalid channel ID: {channel_name}", ephemeral=True)
            return
        
        # Initialize user's channel list if not exists
        if "channels" not in user_data["users"][user_id_str]:
            user_data["users"][user_id_str]["channels"] = []
        
        # Check if channel already exists for this user
        for channel in user_data["users"][user_id_str]["channels"]:
            if channel["id"] == channel_id_int:
                await interaction.followup.send("This channel is already in your list", ephemeral=True)
                return
        
        # Add channel to user's list
        user_data["users"][user_id_str]["channels"].append({
            "id": channel_id_int,
            "name": channel_name
        })
        
        # Save updated data
        with open(user_data_path, "w") as f:
            json.dump(user_data, f, indent=2)
            
        # Reload chat IDs
        await reload_chat_ids()
        
        await interaction.followup.send(f"Added channel: {channel_name} ({channel_id_int})", ephemeral=True)
        
    except ValueError:
        await interaction.followup.send("Please provide a valid numerical ID", ephemeral=True)

# Adding new tg channel by URL
@bot.tree.command(name="addtg", description="Add a TG dm or group to the forwarder")
@app_commands.describe(url="URL of group or dms (Find by using TG web)")
async def addtg(interaction: discord.Interaction, url: str):
    await interaction.response.defer(ephemeral=True)
    
    user_id_str = str(interaction.user.id)
    user_data = load_user_data()
    
    # Check if user has set a destination channel
    if user_id_str not in user_data["users"] or "destination_channel" not in user_data["users"][user_id_str]:
        await interaction.followup.send("You need to set a destination channel first using /set_destination", ephemeral=True)
        return
    
    # Check channel limit for non-paying users
    channel_count = get_user_channel_count(interaction.user.id)
    channel_limit = get_channel_limit(interaction.user.id)
    
    if channel_count >= channel_limit:
        await interaction.followup.send(f"You've reached your limit of {channel_limit} channels. Upgrade to premium for unlimited channels.", ephemeral=True)
        return
    
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
        
        # Initialize user's channel list if not exists
        if "channels" not in user_data["users"][user_id_str]:
            user_data["users"][user_id_str]["channels"] = []
        
        # Check if channel already exists for this user
        for channel in user_data["users"][user_id_str]["channels"]:
            if channel["id"] == tg_id:
                await interaction.followup.send("This channel is already in your list", ephemeral=True)
                return
        
        # Add channel to user's list
        user_data["users"][user_id_str]["channels"].append({
            "id": tg_id,
            "name": channel_name
        })
        
        # Save updated data
        with open(user_data_path, "w") as f:
            json.dump(user_data, f, indent=2)
            
        # Reload chat IDs
        await reload_chat_ids()
        
        await interaction.followup.send(f"Added channel: {channel_name} ({tg_id})", ephemeral=True)
        
    except Exception as e:
        await interaction.followup.send(f"Error adding channel: {str(e)}", ephemeral=True)

# List channels
@bot.tree.command(name="listchannels", description="List all your Telegram channels and verify them")
async def listchannels(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    user_id_str = str(interaction.user.id)
    user_data = load_user_data()
    
    if user_id_str not in user_data["users"] or "channels" not in user_data["users"][user_id_str] or not user_data["users"][user_id_str]["channels"]:
        await interaction.followup.send("You don't have any channels in your list.", ephemeral=True)
        return
    
    # Verify and list all channels
    channels_list = []
    for index, channel_info in enumerate(user_data["users"][user_id_str]["channels"]):
        channel_id = channel_info["id"]
        is_valid, channel_name = await is_valid_channel(channel_id)
        status = "✅ Valid" if is_valid else "❌ Invalid"
        channels_list.append(f"{index+1}. {channel_name} (ID: {channel_id}) - {status}")
    
    # Get user's subscription status
    is_premium = is_owner(interaction.user.id) or is_paying_user(user_id_str)
    tier_status = "Premium (Unlimited Channels)" if is_premium else f"Free Tier ({len(channels_list)}/{FREE_TIER_LIMIT} Channels)"
    
    response = f"**Your Telegram Channels** - {tier_status}\n\n" + "\n".join(channels_list)
    
    # Add destination channel info
    if "destination_channel" in user_data["users"][user_id_str]:
        dest_channel_id = user_data["users"][user_id_str]["destination_channel"]
        dest_channel = bot.get_channel(dest_channel_id)
        if dest_channel:
            response += f"\n\nDestination: {dest_channel.mention}"
        else:
            response += f"\n\nDestination: Unknown Channel (ID: {dest_channel_id})"
    else:
        response += "\n\nNo destination channel set. Use /set_destination to set one."
    
    await interaction.followup.send(response, ephemeral=True)

# Delete a channel by index number
@bot.tree.command(name="deletechannel", description="Delete a Telegram channel by its list number")
@app_commands.describe(index="Channel number from the list (use /listchannels first)")
async def deletechannel(interaction: discord.Interaction, index: int):
    await interaction.response.defer(ephemeral=True)
    
    user_id_str = str(interaction.user.id)
    user_data = load_user_data()
    
    if user_id_str not in user_data["users"] or "channels" not in user_data["users"][user_id_str] or not user_data["users"][user_id_str]["channels"]:
        await interaction.followup.send("You don't have any channels in your list.", ephemeral=True)
        return
    
    # Check if index is valid
    if index < 1 or index > len(user_data["users"][user_id_str]["channels"]):
        await interaction.followup.send(f"Invalid index. Please choose a number between 1 and {len(user_data['users'][user_id_str]['channels'])}.", ephemeral=True)
        return
    
    # Get channel to be deleted
    channel_info = user_data["users"][user_id_str]["channels"][index-1]
    channel_id = channel_info["id"]
    channel_name = channel_info["name"]
    
    # Remove channel
    user_data["users"][user_id_str]["channels"].pop(index-1)
    
    # Save updated data
    with open(user_data_path, "w") as f:
        json.dump(user_data, f, indent=2)
        
    # Reload chat IDs
    await reload_chat_ids()
    
    await interaction.followup.send(f"Deleted {channel_name} (index {index}) from your list.", ephemeral=True)

@bot.tree.command(name="myplan", description="View your current subscription plan")
async def myplan(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    user_id_str = str(user_id)
    
    # Determine user's plan
    if is_owner(user_id):
        plan = "Owner (Unlimited Channels)"
    elif is_paying_user(user_id):
        plan = "Premium (Unlimited Channels)"
    else:
        plan = f"Free Tier (Limit: {FREE_TIER_LIMIT} channels)"
    
    # Get channel count
    channel_count = get_user_channel_count(user_id)
    
    message = f"**Your Plan: {plan}**\n"
    message += f"Channels in use: {channel_count}"
    
    if not is_paying_user(user_id) and not is_owner(user_id):
        message += f"/{FREE_TIER_LIMIT}\n\n"
        message += "To upgrade to Premium with unlimited channels, contact the bot owner."
    else:
        message += "\n"
    
    await interaction.followup.send(message, ephemeral=True)

@bot.tree.command(name="help", description="Show available commands and how to use the bot")
async def help_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    # Determine if user is admin
    is_admin = is_owner(interaction.user.id)
    
    help_message = "**Telegram Forwarder Bot Commands**\n\n"
    
    # User Setup Commands
    help_message += "**Setup Commands:**\n"
    help_message += "• `/set_destination` - Set which Discord channel your Telegram messages should be sent to\n"
    help_message += "• `/myplan` - View your current subscription plan\n\n"
    
    # Channel Management Commands
    help_message += "**Channel Management:**\n"
    help_message += "• `/addtg` - Add a Telegram channel by URL (web.telegram.org or t.me links)\n"
    help_message += "• `/addchannel` - Add a Telegram channel by ID number\n"
    help_message += "• `/listchannels` - View all your channels and check if they're valid\n"
    help_message += "• `/deletechannel` - Remove a channel from your list by its number\n\n"
    
    # Admin Commands
    if is_admin:
        help_message += "**Admin Commands:**\n"
        help_message += "• `/admin_add_paying` - Add a user to premium tier\n"
        help_message += "• `/admin_remove_paying` - Remove a user from premium tier\n"
        help_message += "• `/admin_list_users` - List all users and their status\n"
        help_message += "• `!!sync` - Sync slash commands (in chat)\n\n"
    
    help_message += "**How to use this bot:**\n"
    help_message += "1. First use `/set_destination` to choose where your Telegram messages will be sent\n"
    help_message += "2. Add Telegram channels with `/addtg` or `/addchannel`\n"
    help_message += "3. Check your channels with `/listchannels`\n"
    help_message += f"4. Free users can add up to {FREE_TIER_LIMIT} channels\n"
    
    await interaction.followup.send(help_message, ephemeral=True)

async def main():
    print("Started")
    
    # Start both clients
    try:
        # Start the bot in the background
        bot_task = asyncio.create_task(bot.start(token))
        
        # Wait for the bot to be ready
        while not bot.is_ready():
            await asyncio.sleep(1)
        
        print("Bot is ready, setting up Telegram handlers")
        
        # Set up Telegram handlers
        await reload_chat_ids()
        
        # Keep the bot running
        await bot_task
        
    except Exception as e:
        print(f"Error in main: {str(e)}")

with client:
    client.loop.run_until_complete(main())
    client.run_until_disconnected()
