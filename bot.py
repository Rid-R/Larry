import discord
from discord.ext import commands
import os
from datetime import datetime,timedelta
import random
import json
from dotenv import load_dotenv

USER_DATA_FILE = "user_data.json"
IMAGE_METADATA_FILE = "image_data.json"
IMAGE_FOLDER = "images"

def load_data(filepath):
    try:
        with open(filepath, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return{}
    
def save_data(filepath, data):
    with open(filepath, "w") as file:
        json.dump(data, file, indent=4)

def ensure_user(user_id):
    user_id = str(user_id) 
    if user_id not in users:
        users[user_id] = {
            "coins": 100,
            "power_ups": {"hint_boost": 0, "time_reduction": 0}
        }

users = load_data(USER_DATA_FILE)
image_metadata = load_data(IMAGE_METADATA_FILE)

if not os.path.exists(IMAGE_FOLDER):
    os.makedirs(IMAGE_FOLDER)
    print(f"Created missing folder: {IMAGE_FOLDER}")
if not image_metadata:
    print(f"⚠️ Warning: No image metadata found in {IMAGE_METADATA_FILE}.")


intents = discord.Intents.default()
intents.messages=True
intents.message_content = True
bot = commands.Bot(command_prefix='!',intents=intents)

game_mode = None
current_image = None
correct_time = None
guessing_open = False
start_time = None

@bot.command(name="start_game")
async def start_game(ctx, mode: str = "normal"):

    global game_mode, current_image, correct_time, guessing_open , start_time

    if not image_metadata:
        await ctx.send("⚠️ No image metadata found! Please add data to `image_data.json`.")
        return
    
    current_image = random.choice(list(image_metadata.keys()))
    image_details = image_metadata[current_image]
    correct_time = datetime.strptime(image_details["correct_time"], "%I:%M %p")
    game_mode = mode.lower()
    guessing_open = True
    start_time = datetime.now()

    try:
        with open(f"{IMAGE_FOLDER}/{current_image}", "rb") as img:
            file = discord.File(img)
        await ctx.send("📸 Guess the time this photo was taken!", file=file)
    
    except FileNotFoundError:
        await ctx.send(f"⚠️ Image `{current_image}` not found in the `{IMAGE_FOLDER}` folder!")
        guessing_open = False
        return
    
    if game_mode =="fastest":
        await ctx.send("🏁 Fastest Game Mode! Be the first to guess within 30 minutes of the actual time!")
    else:
        await ctx.send("🕒 Normal Mode: Guess the exact time!")

@bot.command(name="guess_time")
async def guess_time(ctx, *, time: str):
    global guessing_open
    
    if not guessing_open or current_image is None:
        await ctx.send("⚠️ No game is currently active! Use `!start_game` to begin.")
        return
    
    try:
        guessed_time = datetime.strptime(time.strip(), "%I:%M %p")
    except ValueError:
        await ctx.send("❌ Invalid time format! Use `HH:MM AM/PM`. Example: `10:30 PM`.")
        return
    
    user_id = str(ctx.author.id)
    ensure_user(user_id)
    
    if game_mode == "fastest":
        difference = abs((correct_time - guessed_time).total_seconds() / 60) 
        if difference <= 30:
            await ctx.send(f"🎉 {ctx.author.name} wins! The correct time was {correct_time.strftime('%I:%M %p')}.")
            guessing_open = False
        else:
            await ctx.send(f"❌ {ctx.author.name}, Try again!")
    else:  # Normal mode
        
        difference = abs((correct_time - guessed_time).total_seconds()) 
        max_score = 5000
        max_time_diff = 6 * 60 * 60  
        
        
        score = max(0, max_score - int((difference / max_time_diff) * max_score))
        
        
        users[user_id]["coins"] += score//100
        save_data(USER_DATA_FILE, users)
        
        await ctx.send(
            f"🎯 Your guess: {guessed_time.strftime('%I:%M %p')}\n"
            f"✅ Correct time: {correct_time.strftime('%I:%M %p')}\n"
            f"💰 You earned **{score} points**! Total coins: {users[user_id]['coins']}."
        )

       

@bot.command(name="shop")
async def shop(ctx):
    """Display the shop for purchasing power-ups."""
    await ctx.send(
        "🛒 **Shop**:\n"
        "1. Hint Boost - 50 coins\n"
        "2. Time Reduction - 30 coins\n"
        "Use `!buy <item>` to purchase."
    )

@bot.command(name="buy")
async def buy(ctx, item: str):
    """Buy power-ups from the shop."""
    user_id = str(ctx.author.id)
    ensure_user(user_id)

    if item == "hint_boost":
        cost = 50
        if users[user_id]["coins"] >= cost:
            users[user_id]["coins"] -= cost
            users[user_id]["power_ups"]["hint_boost"] += 1
            save_data(USER_DATA_FILE, users)
            await ctx.send("✅ You purchased a Hint Boost!")
        else:
            await ctx.send("❌ You don't have enough coins!")
    elif item == "time_reduction":
        cost = 30
        if users[user_id]["coins"] >= cost:
            users[user_id]["coins"] -= cost
            users[user_id]["power_ups"]["time_reduction"] += 1
            save_data(USER_DATA_FILE, users)
            await ctx.send("✅ You purchased a Time Reduction!")
        else:
            await ctx.send("❌ You don't have enough coins!")
    else:
        await ctx.send("⚠️ Item not recognized! Available items: `hint_boost`, `time_reduction`.")

@bot.command(name="hint")
async def hint(ctx):
    global current_image
    hint_choice=random.choice(["wether","random_event"])
    user_id = str(ctx.author.id)
    ensure_user(user_id)

    if current_image is None:
        await ctx.send("⚠️ No game is currently active! Use `!start_game` to begin.")
        return

    if users[user_id]["power_ups"]["hint_boost"] > 0:
        hint_text = image_metadata[current_image].get(hint_choice, "No hint available for this image.")
        users[user_id]["power_ups"]["hint_boost"] -= 1
        save_data(USER_DATA_FILE, users)
        await ctx.send(f"💡 Hint: {hint_text}")
    else:
        await ctx.send("❌ You don't have any Hint Boosts! Purchase one in the shop with `!buy hint_boost`.")

@bot.command(name="balance")
async def balance(ctx):
    """Check user's coin balance and power-ups."""
    user_id = str(ctx.author.id)
    ensure_user(user_id)
    user_data = users[user_id]
    await ctx.send(
        f"💰 **{ctx.author.name}'s Balance**:\n"
        f"Coins: {user_data['coins']}\n"
        f"Hint Boosts: {user_data['power_ups']['hint_boost']}\n"
        f"Time Reductions: {user_data['power_ups']['time_reduction']}"
    )



@bot.event
async def on_ready():
    print(f"Bot is ready! Logged in as {bot.user}")

@bot.event
async def on_disconnect():
    save_data(USER_DATA_FILE, users)
    print("Bot disconnected. Data saved.")

load_dotenv()   
bot.run(os.getenv("TOKEN"))


        