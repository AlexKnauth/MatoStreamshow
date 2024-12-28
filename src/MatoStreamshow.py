import config
import discord
from discord import app_commands

class MatoStreamshow(discord.Client):
    def __init__(self, *, intents: discord.Intents) -> None:
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

intents = discord.Intents.default()
intents.message_content = True

bot = MatoStreamshow(intents=intents)

@bot.event
async def on_ready():
    print('MatoStreamshow Bot is online!')

@bot.tree.command()
async def ping(interaction: discord.Interaction):
    """
    Replies to ping with pong.

    Parameters
    ----------
    interaction : discord.Interaction
        The interaction object.
    """
    await interaction.response.send_message("Pong!")

def main():
    if config.token == "":
        raise ValueError('config token not found')
    bot.run(config.token)

if __name__ == "__main__":
    main()
