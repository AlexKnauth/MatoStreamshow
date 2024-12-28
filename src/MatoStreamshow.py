import config
import discord
from discord import app_commands
import save

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
    if interaction.guild is None: return
    save.get_guild_data(interaction.guild)
    await interaction.response.send_message("Pong!")

@bot.tree.command(name="twitch-streamer-list")
async def twitch_streamer_list(interaction: discord.Interaction):
    """
    Lists the twitch streamers to show when live.

    Parameters
    ----------
    interaction : discord.Interaction
        The interaction object.
    """
    if interaction.guild is None: return
    l = save.get_guild_data(interaction.guild)["twitch_streamer_list"]
    save.save()
    await interaction.response.send_message(str(l))

@bot.tree.command(name="twitch-streamer-add")
async def twitch_streamer_add(interaction: discord.Interaction, twitch_username: str):
    """
    Adds a twitch streamer to the list to show when live.

    Parameters
    ----------
    interaction : discord.Interaction
        The interaction object.
    twitch_username : str
        The streamer's twitch username.
    """
    if interaction.guild is None: return
    l = save.get_guild_data(interaction.guild)["twitch_streamer_list"]
    if twitch_username in l:
        await interaction.response.send_message("Already contains " + twitch_username)
    else:
        l.append(twitch_username)
        l.sort()
        save.save()
        await interaction.response.send_message("Added " + twitch_username)

@bot.tree.command(name="twitch-streamer-remove")
async def twitch_streamer_remove(interaction: discord.Interaction, twitch_username: str):
    """
    Removes a twitch streamer from the list to show when live.

    Parameters
    ----------
    interaction : discord.Interaction
        The interaction object.
    twitch_username : str
        The streamer's twitch username.
    """
    if interaction.guild is None: return
    l = save.get_guild_data(interaction.guild)["twitch_streamer_list"]
    if twitch_username in l:
        l.remove(twitch_username)
        save.save()
        await interaction.response.send_message("Removed " + twitch_username)
    else:
        await interaction.response.send_message(twitch_username + " not found")

def main():
    if config.token == "":
        raise ValueError('config token not found')
    bot.run(config.token)

if __name__ == "__main__":
    main()
