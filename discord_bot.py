#Discord
import discord
from discord.ext import commands
from discord import app_commands, SyncWebhook
import config
from data_manager import load_user_data, save_new_chat, remove_chat, add_webhook, remove_webhook, get_webhook
from telegram_client import is_valid_channel, client, reload_chat_ids
import json


token = config.discord_token
intents = discord.Intents().all()
bot = commands.Bot(command_prefix="!", intents=intents)
file_path = "channels.json"

@bot.event
async def on_ready():
    print("Logged in as {0.user}".format(bot))

#Sync slash commands
@bot.command(name='sync', description='Sync all the slash commands')
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send('Command tree synced.')

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
        
        user_id = str(interaction.user.id)
        if await save_new_chat(user_id, channel_id_int):
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
        
        try:
            # Convert to integer
            channel_id_int = int(tg_id)
            
            # Check if channel is valid
            is_valid, channel_name = await is_valid_channel(channel_id_int)
            if not is_valid:
                await interaction.followup.send(f"Invalid channel ID: {channel_name}", ephemeral=True)
                return
            
            user_id = str(interaction.user.id)
            if await save_new_chat(user_id, channel_id_int):
                await reload_chat_ids()
                await interaction.followup.send(f"Added channel: {channel_name} ({channel_id_int})", ephemeral=True)
            else:
                await interaction.followup.send("This channel is already in your list", ephemeral=True)

        except ValueError:
            await interaction.followup.send("Please provide a valid numerical ID", ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"Error adding channel: {str(e)}", ephemeral=True)

# List channels
@bot.tree.command(name="listchannels", description="List all your Telegram channels and verify them")
async def listchannels(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    user_id = str(interaction.user.id)
    # Load existing data
    data = await load_user_data(user_id)
    
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

        # Get channel name before deletion for confirmation
        is_valid, channel_name = await is_valid_channel(channel_id_int)
        channel_display = channel_name if is_valid else f"Channel {channel_id_int}"
        

        if await remove_chat(str(interaction.user.id), channel_id_int):
            # Reload chat IDs
            await reload_chat_ids()
            await interaction.followup.send(f"Deleted {channel_display} from your list.", ephemeral=True)
        else:
            await interaction.followup.send("This channel ID was not found in your list.", ephemeral=True)
        
            
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


@bot.tree.command(name="addwebhook", description="Add a Discord webhook URL to receive Telegram messages")
@app_commands.describe(webhook_url="Discord webhook URL")
async def addwebhook(interaction: discord.Interaction, webhook_url: str):
    await interaction.response.defer(ephemeral=True)
    
    try:
        if not webhook_url.startswith("https://discord.com/api/webhooks/") and not webhook_url.startswith("https://discordapp.com/api/webhooks/"):
            await interaction.followup.send("Invalid webhook URL. Please provide a valid Discord webhook URL.", ephemeral=True)
            return
        
        try:
            test_webhook = SyncWebhook.from_url(webhook_url)
            test_webhook.fetch() # Test webhook
        except Exception as e:
            await interaction.followup.send(f"Invalid or inaccessible webhook URL: {str(e)}", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        if await add_webhook(user_id, webhook_url):
            await interaction.followup.send(f"✅ Webhook added successfully!", ephemeral=True)
        else:
            await interaction.followup.send("This webhook is already in your list.", ephemeral=True)
    
    except Exception as e:
        await interaction.followup.send(f"Error adding webhook: {str(e)}", ephemeral=True)

@bot.tree.command(name="removewebhook", description="Remove a Discord webhook URL")
@app_commands.describe(webhook_url="Discord webhook URL to remove")
async def removewebhook(interaction: discord.Interaction, webhook_url: str):
    await interaction.response.defer(ephemeral=True)
    
    try:
        user_id = str(interaction.user.id)
        if await remove_webhook(user_id, webhook_url):
            await interaction.followup.send("✅ Webhook removed successfully!", ephemeral=True)
        else:
            await interaction.followup.send("This webhook was not found in your list.", ephemeral=True)
    
    except Exception as e:
        await interaction.followup.send(f"Error removing webhook: {str(e)}", ephemeral=True)

@bot.tree.command(name="listwebhooks", description="List all your configured webhooks")
async def listwebhooks(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    try:
        user_id = str(interaction.user.id)
        webhooks = await get_webhook(user_id)
        
        if not webhooks:
            await interaction.followup.send("You don't have any webhooks configured.", ephemeral=True)
            return
        
        webhook_list = []
        for index, webhook_url in enumerate(webhooks):
            # Shows only the last part of webhook URL
            webhook_id = webhook_url.split('/')[-2] if len(webhook_url.split('/')) > 2 else "Unknown"
            webhook_list.append(f"{index+1}. .../{webhook_id}")
        
        response = "Your Configured Webhooks:\n" + "\n".join(webhook_list)
        response += "\n\nℹ️ To remove a webhook, copy the full URL from when you added it and use /removewebhook"
        await interaction.followup.send(response, ephemeral=True)
    
    except Exception as e:
        await interaction.followup.send(f"Error listing webhooks: {str(e)}", ephemeral=True)