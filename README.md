# Telegram-to-Discord Forwarder

A simple, Python bot that automatically scrapes text and media from specified Telegram channels and forwards them to a Discord webhook.

This project is built with a decoupled, 5-file architecture to separate the Discord, Telegram scraper, and the "data" logic, making easy to maintain.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/Discord.py-7289DA?style=for-the-badge&logo=discord&logoColor=white)
![Telethon](https://img.shields.io/badge/Telethon-0088CC?style=for-the-badge&logo=python&logoColor=white)
![JSON](https://img.shields.io/badge/JSON-000000?style=for-the-badge&logo=json&logoColor=white)

## About This Project

This project began with a different vision: a multi-user, closed-source, premium Discord bot. The original (more complex) version was designed to have a free tier (limited to 2 channels) and a paid tier for unlimited access.

After building out the core multi-user logic, I made a strategic pivot. I decided to refactor the project into this simpler, more robust, open-source version. This **MVP (Minimum Viable Product)** is designed for a single user to self-host, focusing on stability, clarity, and a clean architecture. This refactor was a great exercise in moving from a single "monolith" script to a professional, decoupled application structure.

## Features

* **Telegram Scraping:** Uses the **Telethon** library to listen for new messages in any number of specified channels.
* **Discord Forwarding:** Uses **Discord Webhooks** to send messages to your channel instantly.
* **Media Support:** Automatically downloads and re-uploads media (images, files) from Telegram to Discord.
* **Simple "Database":** Uses a `channels.json` file to store your channel list and destination.
* **Command Management:** All setup is handled via simple Discord slash commands.

## Architecture
The project is structured into 5 main files, each with its own responsibilities:
1.  **`run.py` (The Starter):** The main entry point. Its *only* job is to use `asyncio.gather()` to start the Discord bot and the Telegram client.
2.  **`config.py`:** Loads all secret keys (API/tokens) from a `.env` file.
3.  **`data_manager.py`:** The *only* file that reads from or writes to `channels.json`. It contains all the "business logic" 
4.  **`discord_bot.py` (UI):** Manages all Discord interactions. It contains all slash commands (`/addchannel`, `/set_destination`, etc.)
5.  **`telegram_client.py` (The Scraper):** Manages all Telegram interactions. It checks if telegram id's being added are valid, listens for new messages, and uses `requests` to forward them to a Discord webhook.

---

## Setup & Installation

Here's how to get the bot running for yourself.

### 1. Prerequisites
* Python 3.8 or newer
* A Telegram account and API keys
* A Discord account and a Webhook URL

### 2. Get Your Keys

* **Telegram:**
    1.  Go to [my.telegram.org](https://my.telegram.org/apps) and log in.
    2.  Create a "New Application."
    3.  Copy your **`api_id`** and **`api_hash`**.
* **Discord:**
    1.  Create a server (or use one you own).
    2.  Go to Server Settings -> Integrations -> Webhooks -> New Webhook.
    3.  Give it a name, choose a channel, and copy the **Webhook URL**.
    4.  You also need a **Bot Token**. Go to the [Discord Developer Portal](https://discord.com/developers/applications), create a "New Application," go to the "Bot" tab, and copy the **token**. You will need to invite this bot to your server.

### 3. Clone the Repository
1.  Clone this repository:
    ```bash
    git clone [https://github.com/AayanAhmed040/Telegram-Discord-Forwarder.git](https://github.com/AayanAhmed040/Telegram-Discord-Forwarder.git)
    cd Telegram-Discord-Forwarder
    ```

2.  Install the required libraries:
    ```bash
    pip install -r requirements.txt
    ```

3.  Create your `.env` file in the main folder. This file is **secret** and should *never* be shared.
    ```.env
    TELEGRAM_API_ID="YOUR_TELEGRAM_API_ID_HERE"
    TELEGRAM_API_HASH="YOUR_TELEGRAM_API_HASH_HERE"
    DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN_HERE"
    ```
4. Create an empty `channels.json` file in the main folder:
    ```json
    {}
    ```
    *Note: Current uploaded channels.json is just an example with no real ID's or webhooks used. You can also delete the current data and use the example file*

5.  Run the bot
    ```bash
    python run.py
    ```
    *(The first time you run it, Telethon will ask you to log in to your Telegram account in the console. Add your phone number with your country code, and no spaces. Then input the code you receive either via telegram or SMS)*

## How to Use

All commands are run from Discord using slash commands:

1.  **`!sync`**
    * In a channel you bot has access to, type `!sync`.
    * Syncs all slash commands. Run this first to ensure all commands are registered.
        * Note: It may take a few minutes for Discord to register the new commands.

2.  **`/addchannel [channel_id]`**
    * Adds a Telegram channel to your scrape list.
    * **How to get the ID:**
        1.  Open Telegram Web.
        2.  Go to the channel you want to scrape.
        3.  The URL will look like: `https://web.telegram.org/a/#-100123456789`
        4.  The ID is the long number, **not including the `-`**. (e.g., `100123456789`)

3.  **`/set_destination [url]`**
    * Paste your Discord Webhook URL here. This is where all messages will be sent.

4. **`Other Commands`**
    * Other slash commands are included in the bot and have desriptions built in.

## Future Improvements
* Add support for forwarding directly to the Discord bot instead of webhooks.
* Clean up code and add more comments/documentation.

## AI Assistance
This projects README was partially generated with the assistance of AI tools to enhance clarity and structure.