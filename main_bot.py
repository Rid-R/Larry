import discord
from discord.ext import commands
import os
from datetime import datetime,timedelta
import random
from dotenv import load_dotenv


intents = discord.Intents.default()
intents.messages=True
intents.message_content = True
bot = commands.Bot(command_prefix='!',intents=intents)

photo_dir = "Photos"

os.makedirs(photo_dir , exist_ok=True)

image_data ={}

def extract_time_from_filename(filename):
    try:
        time_part = filename.split(".")[0] 
        extracted_time = datetime.strptime(time_part, "%H-%M-%S")
        return extracted_time
    except ValueError:
        return None

def calculate_points(actual_time, guessed_time):
    actual_seconds = actual_time.hour * 3600 + actual_time.minute * 60 + actual_time.second
    guessed_seconds = guessed_time.hour * 3600 + guessed_time.minute * 60 + guessed_time.second
    

    delta = max(actual_seconds - guessed_seconds , guessed_seconds - actual_seconds)
    max_time_difference = 3600 * 4
    max_score = 5000
    if delta >= max_time_difference:
        return 0
    points = max_score - (delta / max_time_difference) * max_score
    return max(0,int(points))



@bot.event
async def on_ready():
    print(f'Hello I am {bot.user} , call me any time to satrt guessing')

@bot.command(name="load_images")
async def load_images(ctx):
    """Loaf images from the photo directory and assign timestams."""
    images = [f for f in os.listdir(photo_dir) if f.lower().endswith(('png',"jpg","jpeg","gif"))]
    if not images:
        await ctx.send("no img found")
        return
    
    for image in images:
        if image not in image_data:
            extracted_time = extract_time_from_filename(image)
            if extracted_time:
                image_data[image] = extracted_time
                await ctx.send(f"Loaded image: {image} with timestamp{extracted_time.strftime('%H:%M:%S')}.")
            else:
                await ctx.send(f"Skipped image: {image}. Filename is not correct")
    await ctx.send(f"Loaded {len(image_data)} images.")

@bot.command(name="guess")
async def guess(ctx):
    """Randomly select an image for the user to guess its time."""
    if not image_data:
        await ctx.send("No images have been loaded yet.")
        return

    image_name, actual_time = random.choice(list(image_data.items()))
    filepath = os.path.join(photo_dir, image_name)
    with open(filepath, "rb") as file:
        discord_file = discord.File(file, filename=image_name)
        await ctx.send(f"Here's an image! Try guessing when it was clicked. Respond with your guess in HH:MM:SS format.", file=discord_file)

    def check(message):
        return message.author == ctx.author and message.content.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'))  

    try:
        guess_message = await bot.wait_for('message', check=check, timeout=60.0) 

        try:
            guessed_time = datetime.strptime(guess_message.content, "%H:%M:%S").time()
            guessed_datetime = datetime.combine(datetime.today(), guessed_time)
            points = calculate_points(actual_time, guessed_datetime)
            await ctx.send(f"Actual time: {actual_time.strftime('%H:%M:%S')}.\nYour guess: {guess_message.content}.\nYou scored {points} points!")

        except ValueError:
            await ctx.send("Invalid time format. Please use HH:MM:SS.")
    
    except TimeoutError:
        await ctx.send("You took too long to respond! Try again.")

@bot.command(name="list_images")
async def list_images(ctx):
    """List all loaded images."""
    if not image_data:
        await ctx.send("No images have been loaded yet.")
        return

    image_list = "\n".join(image_data.keys())
    await ctx.send(f"Available images:\n{image_list}")

@bot.command(name="reset_images")
async def reset_images(ctx):
    """Reset the loaded images and timestamps."""
    image_data.clear()
    await ctx.send("All loaded images and timestamps have been reset.")
load_dotenv()   
bot.run(os.getenv("TOKEN"))
