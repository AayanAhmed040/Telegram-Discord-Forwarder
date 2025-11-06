import json

file_path = "channels.json"

    
async def load_user_data(user_id: str):
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    if user_id not in data:
        data[user_id] = {"id": [], "webhook": []}
        await save_data(data)

    return data

async def save_data(data):
    with open(file_path, "w") as file:
        json.dump(data, file, indent=2)

async def load_chat_ids():
    """
    This function loads chat IDs from a JSON file.
    """
    try:
        with open("channels.json", "r") as f:
            data = json.load(f)
            all_chat_ids = []
        for user_id in data:
            all_chat_ids.extend(data[user_id]["id"])
        return list(set(all_chat_ids))  # Remove duplicates
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is invalid, create an empty structure
        with open("channels.json", "w") as f:
            json.dump({}, f)
        return []

async def save_new_chat(user_id: str, channel_id: int) -> bool:
    """
    This function saves a new chat ID for the user.
    """
    data = await load_user_data(user_id)

    if channel_id not in data[user_id]["id"]:
        data[user_id]["id"].append(channel_id)

        await save_data(data)
        return True
    else:
        return False
    
async def remove_chat(user_id: str, channel_id: int) -> bool:
    """
    This function removes a chat ID for the user.
    """
    data = await load_user_data(user_id)

    if user_id in data and channel_id in data[user_id]["id"]:
        data[user_id]["id"].remove(channel_id)

        await save_data(data)
        return True
    else:
        return False
    
def get_webhook():
    """
    Get all webhook URLs from all users.
    """
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    
    all_webhooks = []
    for user_id in data:
        if "webhook" in data[user_id]:
            all_webhooks.extend(data[user_id]["webhook"])
    
    return list(set(all_webhooks))  # Remove duplicates


async def add_webhook(user_id: str, webhook_url: str) -> bool:
    data = await load_user_data(user_id)

    if webhook_url not in data[user_id]["webhook"]:
        data[user_id]["webhook"].append(webhook_url)

        await save_data(data)
        return True
    else:
        return False
    
async def remove_webhook(user_id: str, webhook_url: str) -> bool:
    data = await load_user_data(user_id)

    if user_id in data and webhook_url in data[user_id]["webhook"]:
        data[user_id]["webhook"].remove(webhook_url)

        await save_data(data)
        return True
    else:
        return False
    
