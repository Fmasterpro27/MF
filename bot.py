import discord
from discord.ext import commands
import json
import config
import os

intents = discord.Intents.all()


bot = commands.Bot(command_prefix='m!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    await bot.change_presence(
        activity=discord.Game(name="with your mom 😏"),
        status=discord.Status.online
    )
    await bot.tree.sync()
    print('Commands synced!')
    
    # Load all cogs from the 'cogs' directory
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            bot.load_extension(f'cogs.{filename[:-3]}')

    

if __name__ == '__main__':
    bot.run(config.TOKEN)