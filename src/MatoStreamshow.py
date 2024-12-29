import config
import discord
from discord import app_commands
from discord.ext.tasks import loop
import save
from twitchAPI.twitch import Twitch

api: Twitch | None = None

if not config.twitch_api_id:
    print("config twitch_api_id not found")
if not config.twitch_api_secret:
    print("config twitch_api_secret not found")

class MatoStreamshow(discord.Client):
    def __init__(self, *, intents: discord.Intents) -> None:
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        await bot.setup_twitch()

    async def setup_twitch(self):
        global api
        if api is not None:
            print("Setup attempted when already set up, ignoring")
            return
        if not config.twitch_api_id or not config.twitch_api_secret:
            print("Setup attempted when twitch api info not present, ignoring")
            return
        api = await Twitch(config.twitch_api_id, config.twitch_api_secret, True, [])

    @loop(minutes=1)
    async def TwitchListen(self):
        print("begin TwitchListen")
        for g in save.get_guild_ids():
            d = save.get_guild_data(g)
            l = d["twitch_streamer_list"]
            cats = d["twitch_category_list"]
            dc = bot.get_channel(d["channel_id"])
            dcms = {}
            async for m in dc.history():
                if m.author.id == self.user.id:
                    name = m.embeds[0].author.name
                    if name in dcms:
                        await m.delete()
                    else:
                        dcms[name] = m
            twitch_channels = api.get_streams(stream_type="live", user_login=l, first=100)
            names = set()
            async for tc in twitch_channels:
                if len(cats) == 0 or tc.game_name in cats:
                    names.add(tc.user_name)
                    text = "**" + tc.user_name + "** is live! playing " + tc.game_name
                    url = "https://www.twitch.tv/" + tc.user_name
                    thumb = tc.thumbnail_url.replace("{width}", "240").replace("{height}", "160")
                    if tc.user_name in dcms:
                        # TODO: edit message if out of date
                        pass
                    else:
                        embed = discord.Embed(title=tc.title, url=url, description=tc.game_name)
                        embed.set_author(name=tc.user_name, url=url)
                        embed.set_thumbnail(url=thumb)
                        await dc.send(text, embed=embed)
            for name, dcm in dcms.items():
                if not name in names:
                    await dcm.delete()
        print("end TwitchListen")

intents = discord.Intents.default()
intents.message_content = True

bot = MatoStreamshow(intents=intents)

@bot.event
async def on_ready():
    bot.TwitchListen.start()
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
    save.get_guild_data(str(interaction.guild.id))["name"] = interaction.guild.name
    await interaction.response.send_message("Pong!")

@bot.tree.command()
async def channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """
    Sets the text channel to send stream live messages to.

    Parameters
    ----------
    interaction : discord.Interaction
        The interaction object.
    channel : discord.TextChannel
        The text channel to send stream live messages to.
    """
    if interaction.guild is None: return
    d = save.get_guild_data(str(interaction.guild.id))
    d["name"] = interaction.guild.name
    d["channel_id"] = channel.id
    save.save()
    await interaction.response.send_message("Posting stream live messages in " + channel.mention)

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
    d = save.get_guild_data(str(interaction.guild.id))
    d["name"] = interaction.guild.name
    l = d["twitch_streamer_list"]
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
    d = save.get_guild_data(str(interaction.guild.id))
    d["name"] = interaction.guild.name
    l = d["twitch_streamer_list"]
    if twitch_username in l:
        await interaction.response.send_message("Already contains " + twitch_username)
    elif 100 <= len(l):
        await interaction.response.send_message("You can only specify up to 100 names (Twitch API constraint)")
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
    d = save.get_guild_data(str(interaction.guild.id))
    d["name"] = interaction.guild.name
    l = d["twitch_streamer_list"]
    if twitch_username in l:
        l.remove(twitch_username)
        save.save()
        await interaction.response.send_message("Removed " + twitch_username)
    else:
        await interaction.response.send_message(twitch_username + " not found")

@bot.tree.command(name="twitch-category-list")
async def twitch_category_list(interaction: discord.Interaction):
    """
    Lists the twitch categories to filter by.

    Parameters
    ----------
    interaction : discord.Interaction
        The interaction object.
    """
    if interaction.guild is None: return
    d = save.get_guild_data(str(interaction.guild.id))
    d["name"] = interaction.guild.name
    l = d["twitch_category_list"]
    save.save()
    await interaction.response.send_message(str(l))

@bot.tree.command(name="twitch-category-add")
async def twitch_category_add(interaction: discord.Interaction, twitch_category: str):
    """
    Adds a twitch category to the list to filter by.

    Parameters
    ----------
    interaction : discord.Interaction
        The interaction object.
    twitch_category : str
        The category ???.
    """
    if interaction.guild is None: return
    d = save.get_guild_data(str(interaction.guild.id))
    d["name"] = interaction.guild.name
    l = d["twitch_category_list"]
    if twitch_category in l:
        await interaction.response.send_message("Already contains " + twitch_category)
    else:
        l.append(twitch_category)
        l.sort()
        save.save()
        await interaction.response.send_message("Added " + twitch_category)

@bot.tree.command(name="twitch-category-remove")
async def twitch_category_remove(interaction: discord.Interaction, twitch_category: str):
    """
    Removes a twitch category from the list to filter by.

    Parameters
    ----------
    interaction : discord.Interaction
        The interaction object.
    twitch_category : str
        The category ???.
    """
    if interaction.guild is None: return
    d = save.get_guild_data(str(interaction.guild.id))
    d["name"] = interaction.guild.name
    l = d["twitch_category_list"]
    if twitch_category in l:
        l.remove(twitch_category)
        save.save()
        await interaction.response.send_message("Removed " + twitch_category)
    else:
        await interaction.response.send_message(twitch_category + " not found")

def main():
    if config.token == "":
        raise ValueError('config token not found')
    bot.run(config.token)

if __name__ == "__main__":
    main()
