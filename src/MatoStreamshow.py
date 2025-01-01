import config
import discord
from discord import app_commands
from discord.ext.tasks import loop
import re
import save
from twitchAPI.twitch import Twitch

api: Twitch | None = None

if not config.twitch_api_id:
    print("config twitch_api_id not found")
if not config.twitch_api_secret:
    print("config twitch_api_secret not found")

def parse_twitch_username(s: str) -> str | None:
    m = re.search("\s*(.*@|.*twitch.tv/)?(\w+)\s*", s)
    return m and m.group(2)

def plain(s: str) -> str:
    return discord.utils.escape_markdown(s).replace("://", "\u200b:\u200b/\u200b/\u200b").replace(".", "\u200b.\u200b")

def code(s: str) -> str:
    if s == "":
        return "` `"
    else:
        return "``" + s.replace("`", "\u200b`\u200b") + "``"

def codeblock(s: str, language: str = "") -> str:
    return "```" + language + "\n" + s.replace("`", "\u200b`\u200b") + "\n```"

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
        for g in save.get_guild_ids():
            d = save.get_guild_data(g)
            l = d["twitch_streamer_list"]
            cats = d["twitch_category_list"]
            dc_id = d["channel_id"]
            dsr_id = d["streamer_role_id"]
            dlr_id = d["live_role_id"]
            if not (dc_id and dc_id != 0):
                continue
            dc = bot.get_channel(dc_id)
            streamer_members = set()
            live_members = set()
            if dsr_id and dlr_id and dsr_id != 0 and dlr_id != 0:
                guild = self.get_guild(int(g))
                dsr = guild.get_role(dsr_id)
                dlr = guild.get_role(dlr_id)
                for m in dsr.members:
                    streamer_members.add(m)
                for m in streamer_members:
                    for a in m.activities:
                        if isinstance(a, discord.Streaming):
                            print(a.platform)
                            print(a.twitch_name)
                            print(a.name)
                            print(a.game)
                            print(a.url)
                            live_members.add(m)
                    if m in live_members:
                        await m.add_roles(dlr, reason="Streaming Live")
                    else:
                        await m.remove_roles(dlr, reason="Not Streaming Live")
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
                    text = "**" + plain(tc.user_name) + "** is live! Playing " + plain(tc.game_name)
                    url = "https://www.twitch.tv/" + tc.user_name
                    thumb = tc.thumbnail_url.replace("{width}", "320").replace("{height}", "180")
                    if tc.user_name in dcms:
                        m = dcms[tc.user_name]
                        if m.content != text or len(m.embeds) == 0 or m.embeds[0].title != tc.title:
                            embed = discord.Embed(colour=discord.Colour.purple(), title=tc.title, url=url, description=tc.game_name)
                            embed.set_author(name=tc.user_name, url=url)
                            embed.set_thumbnail(url=thumb)
                            await m.edit(content=text, embed=embed)
                    else:
                        embed = discord.Embed(colour=discord.Colour.purple(), title=tc.title, url=url, description=tc.game_name)
                        embed.set_author(name=tc.user_name, url=url)
                        embed.set_thumbnail(url=thumb)
                        await dc.send(text, embed=embed)
            for name, dcm in dcms.items():
                if not name in names:
                    await dcm.delete()

intents = discord.Intents.default()
intents.presences = True
intents.members = True
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
@app_commands.default_permissions(manage_channels=True)
@app_commands.checks.has_permissions(manage_channels=True)
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

@bot.tree.command(name="streamer-role")
@app_commands.default_permissions(manage_roles=True)
@app_commands.checks.has_permissions(manage_roles=True)
async def streamer_role(interaction: discord.Interaction, role: discord.Role):
    """
    Sets the role to check streams for.

    Parameters
    ----------
    interaction : discord.Interaction
        The interaction object.
    role : discord.Role
        The role to check streams for.
    """
    if interaction.guild is None: return
    d = save.get_guild_data(str(interaction.guild.id))
    d["name"] = interaction.guild.name
    d["streamer_role_id"] = role.id
    save.save()
    await interaction.response.send_message("Streamer role set to " + plain(role.name))

@bot.tree.command(name="live-role")
@app_commands.default_permissions(manage_roles=True)
@app_commands.checks.has_permissions(manage_roles=True)
async def live_role(interaction: discord.Interaction, role: discord.Role):
    """
    Sets the role to grant streamers when live.

    Parameters
    ----------
    interaction : discord.Interaction
        The interaction object.
    role : discord.Role
        The role to grant streamers when live.
    """
    if interaction.guild is None: return
    d = save.get_guild_data(str(interaction.guild.id))
    d["name"] = interaction.guild.name
    d["live_role_id"] = role.id
    save.save()
    await interaction.response.send_message("Live role set to " + plain(role.name))

@bot.tree.command(name="twitch-streamer-list")
@app_commands.default_permissions(manage_roles=True)
@app_commands.checks.has_permissions(manage_roles=True)
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
    await interaction.response.send_message(codeblock(repr(l), language="python"))

@bot.tree.command(name="twitch-streamer-add")
@app_commands.default_permissions(manage_roles=True)
@app_commands.checks.has_permissions(manage_roles=True)
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
    tu = parse_twitch_username(twitch_username)
    if tu == None:
        await interaction.response.send_message(code(repr(twitch_username)) + " is not a valid twitch username")
    elif tu in l:
        await interaction.response.send_message("Already contains " + plain(tu))
    elif 100 <= len(l):
        await interaction.response.send_message("You can only specify up to 100 names (Twitch API constraint)")
    else:
        l.append(tu)
        l.sort(key=str.casefold)
        save.save()
        await interaction.response.send_message("Added " + plain(tu))

@bot.tree.command(name="twitch-streamer-remove")
@app_commands.default_permissions(manage_roles=True)
@app_commands.checks.has_permissions(manage_roles=True)
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
    tu = parse_twitch_username(twitch_username)
    if tu == None:
        await interaction.response.send_message(code(repr(twitch_username)) + " is not a valid twitch username")
    elif tu in l:
        l.remove(tu)
        save.save()
        await interaction.response.send_message("Removed " + plain(tu))
    else:
        await interaction.response.send_message(plain(tu) + " not found")

@bot.tree.command(name="twitch-category-list")
@app_commands.default_permissions(manage_roles=True)
@app_commands.checks.has_permissions(manage_roles=True)
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
    await interaction.response.send_message(codeblock(repr(l), language="python"))

@bot.tree.command(name="twitch-category-add")
@app_commands.default_permissions(manage_roles=True)
@app_commands.checks.has_permissions(manage_roles=True)
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
        await interaction.response.send_message("Already contains " + plain(twitch_category))
    else:
        l.append(twitch_category)
        l.sort(key=str.casefold)
        save.save()
        await interaction.response.send_message("Added " + plain(twitch_category))

@bot.tree.command(name="twitch-category-remove")
@app_commands.default_permissions(manage_roles=True)
@app_commands.checks.has_permissions(manage_roles=True)
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
        await interaction.response.send_message("Removed " + plain(twitch_category))
    else:
        await interaction.response.send_message(plain(twitch_category) + " not found")

def main():
    if config.token == "":
        raise ValueError('config token not found')
    bot.run(config.token)

if __name__ == "__main__":
    main()
