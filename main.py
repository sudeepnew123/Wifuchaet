import os
import hashlib
import json
import requests
from flask import Flask, request
import telebot
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

WAIFU_FOLDER = "waifus"
WAIFU_DATA_FILE = "waifu_data.json"

os.makedirs(WAIFU_FOLDER, exist_ok=True)
if not os.path.exists(WAIFU_DATA_FILE):
    with open(WAIFU_DATA_FILE, "w") as f:
        json.dump({}, f)

def load_waifu_data():
    with open(WAIFU_DATA_FILE, "r") as f:
        return json.load(f)

def save_waifu_data(data):
    with open(WAIFU_DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_image_hash(image_bytes):
    return hashlib.md5(image_bytes).hexdigest()

def save_image(image_bytes, hash_name):
    path = os.path.join(WAIFU_FOLDER, f"{hash_name}.jpg")
    with open(path, "wb") as f:
        f.write(image_bytes)

def search_trace_moe(image_bytes):
    response = requests.post("https://api.trace.moe/search", files={"image": image_bytes})
    if response.status_code == 200:
        result = response.json()
        if result["result"]:
            r = result["result"][0]
            return {
    "anime": r.get("anime", "Unknown"),
    "character": r.get("character") or r.get("filename", "Unknown"),
    "episode": f"Ep {r.get('episode', '?')}",
    "timestamp": f"{int(r['from']//60)}:{int(r['from']%60):02}"
            }
    return None

@bot.message_handler(commands=["name"])
def handle_name(message):
    if not message.reply_to_message or not message.reply_to_message.photo:
        bot.reply_to(message, "🌚 Reply to a waifu image with /name to identify.")
        return

    file_id = message.reply_to_message.photo[-1].file_id
    file_info = bot.get_file(file_id)
    image_bytes = bot.download_file(file_info.file_path)

    hash_name = get_image_hash(image_bytes)
    waifu_data = load_waifu_data()

    if hash_name in waifu_data:
        data = waifu_data[hash_name]
        source = "📂 Source: Local Database 🌚"
    else:
        result = search_trace_moe(image_bytes)
        if not result:
            bot.reply_to(message, "😿 Sorry, couldn't find the waifu.")
            return
        waifu_data[hash_name] = result
        save_waifu_data(waifu_data)
        save_image(image_bytes, hash_name)
        data = result
        source = "🔍 Source: trace.moe"

    reply_text = (
        f"🔍 Character: {data['character']}\n"
        f"🎞 Anime: {data['anime']}\n"
        f"⏱ Scene: {data['episode']} - {data['timestamp']}\n"
        f"{source}"
    )
    bot.reply_to(message, reply_text)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "OK"

@app.route("/", methods=["GET"])
def index():
    return "Bot Running"

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"https://wifuchaet.onrender.com/{TOKEN}")
    app.run(host="0.0.0.0", port=10000)
