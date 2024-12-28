import config
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print('MatoStreamshow Bot is online!')

@bot.tree.command()
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

def main():
    if config.token == "":
        raise ValueError('config token not found')
    bot.tree.sync()
    bot.run(config.token)

if __name__ == "__main__":
    main()
