from collections import namedtuple

import aiohttp
import config
import discord
from discord import app_commands
from discord.ext.tasks import loop
import itertools
import re
import save
import traceback
import twitchAPI
from twitchAPI.twitch import Twitch

api: Twitch | None = None

if (not config.twitch_api_id) or config.twitch_api_id == "":
    print("config twitch_api_id not found")
if (not config.twitch_api_secret) or config.twitch_api_secret == "":
    print("config twitch_api_secret not found")

# ---------------------------------------------------------

# Twitch info processing

GlobalLiveInfo = namedtuple('GlobalLiveInfo', ['game_name', 'title', 'url', 'thumbnail_url', 'profile_image_url', 'started_at', 'game_image_url'])

ServerLiveInfo = namedtuple('ServerLiveInfo', ['display_name', 'display_avatar', 'has_streamer_role'])

global_live_infos: dict[str, GlobalLiveInfo] = {}
server_live_infoss: dict[str, dict[str, ServerLiveInfo]] = {}

def parse_twitch_username(s: str) -> str | None:
    m = re.search(r"\s*(.*@|.*twitch.tv/)?(\w+)\s*", s)
    return m and m.group(2)

thumbnail_url_template = None
invalid_thumbnail_url_templates = []

def guess_thumbnail_url_template(user_name: str, thumbnail_url: str) -> str | None:
    name = user_name.casefold()
    template = thumbnail_url.replace(name, "{user_name}", 1)
    if template.find(name) != -1:
        return None
    return template

def guess_thumbnail_url(user_name: str, template: str | None) -> str | None:
    if not template:
        return None
    return template.replace("{user_name}", user_name.casefold(), 1)

def recover_case(s: str, l) -> str:
    scf = s.casefold()
    for e in l:
        if scf == e.casefold():
            return e
    return s

# ---------------------------------------------------------

# Discord message output utils

def plain(s: str) -> str:
    return discord.utils.escape_markdown(s).replace("://", "\u200b:\u200b/\u200b/\u200b").replace(".", "\u200b.\u200b")

def code(s: str) -> str:
    if s == "":
        return "` `"
    else:
        return "``" + s.replace("`", "\u200b`\u200b") + "``"

def codeblock(s: str, language: str = "") -> str:
    return "```" + language + "\n" + s.replace("`", "\u200b`\u200b") + "\n```"

# ---------------------------------------------------------

# Main MatoStreamshow class

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
        if not config.twitch_api_id or not config.twitch_api_secret or config.twitch_api_id == "" or config.twitch_api_secret == "":
            print("Setup attempted when twitch api info not present, ignoring")
            return
        api = await Twitch(config.twitch_api_id, config.twitch_api_secret, True, [])

    @loop(minutes=1)
    async def TwitchListen(self):
        global thumbnail_url_template
        global global_live_infos
        global server_live_infoss
        global_valid_keys: set[str] = set()
        server_valid_keyss: dict[str, set[str]] = {}
        try:
            for g in save.get_guild_ids():
                d = save.get_guild_data(g)
                dc_id = d["channel_id"]
                if not (dc_id and dc_id != 0):
                    continue
                cap_l = d["twitch_streamer_list"]
                dsr_id = d["streamer_role_id"]
                dlr_id = d["live_role_id"]
                server_live_infoss[g] = {}
                server_live_infos = server_live_infoss[g]
                server_valid_keyss[g] = set()
                server_valid_keys = server_valid_keyss[g]
                streamer_members: set[discord.Member] = set()
                live_members: set[discord.Member] = set()
                if not (dsr_id and dsr_id != 0):
                    continue
                guild = self.get_guild(int(g))
                dsr = guild.get_role(dsr_id)
                for m in dsr.members:
                    streamer_members.add(m)
                for m in streamer_members:
                    for a in m.activities:
                        if isinstance(a, discord.Streaming) and a.platform == "Twitch":
                            live_members.add(m)
                            lower_name = a.twitch_name.casefold()
                            global_live_infos[lower_name] = GlobalLiveInfo(
                                game_name=a.game,
                                title=a.name,
                                url=a.url,
                                thumbnail_url=None,
                                profile_image_url=None,
                                started_at=a.created_at,
                                game_image_url=None,
                            )
                            server_live_infos[lower_name] = ServerLiveInfo(
                                display_name=m.display_name,
                                display_avatar=m.display_avatar,
                                has_streamer_role=True,
                            )
                            global_valid_keys.add(lower_name)
                            server_valid_keys.add(lower_name)
                if not (dlr_id and dlr_id != 0):
                    continue
                try:
                    dlr = guild.get_role(dlr_id)
                    for m in streamer_members:
                        if m in live_members:
                            await m.add_roles(dlr, reason="Streaming Live")
                        else:
                            await m.remove_roles(dlr, reason="Not Streaming Live")
                except discord.Forbidden as e:
                    print("MatoStreamshow needs permission to manage the live role")
                    traceback.print_exception(e)
            lower_set_all = set()
            for g in save.get_guild_ids():
                d = save.get_guild_data(g)
                dc_id = d["channel_id"]
                if not (dc_id and dc_id != 0):
                    continue
                cap_l = d["twitch_streamer_list"]
                lower_set_all.update((u.casefold() for u in cap_l))
            hadTwitchBackendException = False
            try:
                for batch in itertools.batched(lower_set_all, 100):
                    streams = api.get_streams(stream_type="live", user_login=list(batch), first=100)
                    async for stream in streams:
                        thumb = stream.thumbnail_url.replace("{width}", "320").replace("{height}", "180")
                        if not thumbnail_url_template:
                            template = guess_thumbnail_url_template(stream.user_name, thumb)
                            if not template in invalid_thumbnail_url_templates:
                                thumbnail_url_template = template
                                print("current thumbnail_url_template: " + thumbnail_url_template)
                        elif guess_thumbnail_url(stream.user_name, thumbnail_url_template) != thumb:
                            print("invalid thumbnail_url_template: " + thumbnail_url_template)
                            invalid_thumbnail_url_templates.append(thumbnail_url_template)
                            thumbnail_url_template = None
                        url = "https://www.twitch.tv/" + stream.user_name
                        lower_name = stream.user_name.casefold()
                        if not lower_name in global_valid_keys:
                            global_live_infos[lower_name] = GlobalLiveInfo(
                                game_name=stream.game_name,
                                title=stream.title,
                                url=url,
                                thumbnail_url=thumb,
                                profile_image_url=None,
                                started_at=stream.started_at,
                                game_image_url=None,
                            )
                            global_valid_keys.add(lower_name)
            except twitchAPI.type.TwitchBackendException as e:
                hadTwitchBackendException = True
                print("Twitch API Server Error in TwitchListen")
                traceback.print_exception(e)
            if not hadTwitchBackendException:
                for lower_name in set(global_live_infos.keys()):
                    if not lower_name in global_valid_keys:
                        global_live_infos.pop(lower_name)
            for g in save.get_guild_ids():
                d = save.get_guild_data(g)
                dc_id = d["channel_id"]
                if not (dc_id and dc_id != 0):
                    continue
                server_live_infos = server_live_infoss[g]
                server_valid_keys = server_valid_keyss[g]
                cap_l = d["twitch_streamer_list"]
                cats = d["twitch_category_list"]
                for cap_name in cap_l:
                    lower_name = cap_name.casefold()
                    if lower_name in global_valid_keys:
                        stream = global_live_infos[lower_name]
                        if (not lower_name in server_valid_keys) and (len(cats) == 0 or stream.game_name in cats):
                            server_live_infos[lower_name] = ServerLiveInfo(
                                display_name=cap_name,
                                display_avatar=None,
                                has_streamer_role=False,
                            )
                            server_valid_keys.add(lower_name)
                if not hadTwitchBackendException:
                    for lower_name in set(server_live_infos.keys()):
                        if not lower_name in server_valid_keys:
                            server_live_infos.pop(lower_name)
            avatar_unknowns = set()
            for g in save.get_guild_ids():
                d = save.get_guild_data(g)
                dc_id = d["channel_id"]
                if not (dc_id and dc_id != 0):
                    continue
                server_live_infos = server_live_infoss[g]
                avatar_unknowns.update((u for u, i in server_live_infos.items() if i.display_avatar == None))
            try:
                for batch in itertools.batched(avatar_unknowns, 100):
                    users = api.get_users(logins=list(batch))
                    async for user in users:
                        lower_name = user.login.casefold()
                        global_info = global_live_infos[lower_name]
                        global_live_infos[lower_name] = global_info._replace(profile_image_url=user.profile_image_url)
            except twitchAPI.type.TwitchBackendException as e:
                hadTwitchBackendException = True
                print("Twitch API Server Error in TwitchListen")
                traceback.print_exception(e)
            game_image_unknowns = set()
            game_images = {}
            for global_info in global_live_infos.values():
                if global_info.game_name in game_images:
                    game_image_unknowns.remove(global_info.game_name)
                elif global_info.game_name in game_image_unknowns:
                    continue
                elif global_info.game_image_url:
                    game_images[global_info.game_name] = global_info.game_image_url
                    game_image_unknowns.remove(global_info.game_name)
                else:
                    game_image_unknowns.add(global_info.game_name)
            try:
                for batch in itertools.batched(game_image_unknowns, 100):
                    games = api.get_games(names=list(batch))
                    async for game in games:
                        game_images[game.name] = game.box_art_url.replace("{width}", "60").replace("{height}", "80")
            except twitchAPI.type.TwitchBackendException as e:
                hadTwitchBackendException = True
                print("Twitch API Server Error in TwitchListen")
                traceback.print_exception(e)
            for g in save.get_guild_ids():
                d = save.get_guild_data(g)
                dc_id = d["channel_id"]
                if not (dc_id and dc_id != 0):
                    continue
                cap_l = d["twitch_streamer_list"]
                server_live_infos = server_live_infoss[g]
                dc = bot.get_channel(dc_id)
                dcms = {}
                try:
                    async for m in dc.history():
                        if m.author.id == self.user.id and 1 <= len(m.embeds):
                            name = m.embeds[0].author.name.casefold()
                            if name in dcms:
                                # ** there can only be one! **
                                await m.delete()
                            else:
                                dcms[name] = m
                except discord.Forbidden as e:
                    print("MatoStreamshow needs permission to read message history")
                    traceback.print_exception(e)
                try:
                    for name, server_info in server_live_infos.items():
                        cap_name = recover_case(name, cap_l)
                        global_info = global_live_infos[name]
                        plain_game = plain(global_info.game_name)
                        text = "**" + plain(server_info.display_name) + "** is live! Playing " + plain_game
                        title = plain(global_info.title)
                        thumb = global_info.thumbnail_url or guess_thumbnail_url(name, thumbnail_url_template)
                        icon = server_info.display_avatar or global_info.profile_image_url
                        game_icon = global_info.game_image_url or game_images.get(global_info.game_name)
                        if name in dcms:
                            m = dcms[name]
                            if m.content != text or len(m.embeds) == 0 or m.embeds[0].title != title:
                                embed = discord.Embed(colour=discord.Colour.purple(), title=title, url=global_info.url)
                                embed.set_author(name=cap_name, url=global_info.url, icon_url=icon)
                                embed.set_thumbnail(url=thumb)
                                embed.set_footer(text=plain_game, icon_url=game_icon)
                                if global_info.started_at:
                                    embed.timestamp = global_info.started_at
                                await m.edit(content=text, embed=embed)
                        else:
                            embed = discord.Embed(colour=discord.Colour.purple(), title=title, url=global_info.url)
                            embed.set_author(name=cap_name, url=global_info.url, icon_url=icon)
                            embed.set_thumbnail(url=thumb)
                            embed.set_footer(text=plain_game, icon_url=game_icon)
                            if global_info.started_at:
                                embed.timestamp = global_info.started_at
                            await dc.send(text, embed=embed)
                except discord.Forbidden as e:
                    print("MatoStreamshow needs permission to send messages in:")
                    print("  Server name: " + d["name"])
                    print("  Channel id: " + str(dc_id))
                    traceback.print_exception(e)
                if not hadTwitchBackendException:
                    for name, dcm in dcms.items():
                        if not name in server_live_infos:
                            await dcm.delete()
        except discord.DiscordServerError as e:
            print("Discord Server Error in TwitchListen")
            traceback.print_exception(e)
        except aiohttp.client_exceptions.ClientConnectorError as e:
            print("Client Connector Error in TwitchListen")
            traceback.print_exception(e)

intents = discord.Intents.default()
intents.presences = True
intents.members = True
intents.message_content = True

bot = MatoStreamshow(intents=intents)

@bot.event
async def on_ready():
    if not bot.TwitchListen.is_running():
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
    if channel.permissions_for(interaction.guild.me).send_messages:
        d["channel_id"] = channel.id
        save.save()
        await interaction.response.send_message("Posting stream live messages in " + channel.mention)
    elif d["channel_id"] == 0:
        d["channel_id"] = channel.id
        save.save()
        await interaction.response.send_message("Warning: MatoStreamshow needs permission to send messages in " + channel.mention)
    else:
        await interaction.response.send_message("Error: MatoStreamshow needs permission to send messages in " + channel.mention)

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
    if role.is_assignable():
        d["live_role_id"] = role.id
        save.save()
        await interaction.response.send_message("Live role set to " + plain(role.name))
    elif d["live_role_id"] == 0:
        d["live_role_id"] = role.id
        save.save()
        await interaction.response.send_message("Warning: MatoStreamshow can't assign "+ plain(role.name) + " until MatoStreamshow's role is moved above it")
    else:
        await interaction.response.send_message("Error: MatoStreamshow can't assign "+ plain(role.name) + " unless MatoStreamshow's role is moved above it")

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
    cap_l = d["twitch_streamer_list"]
    save.save()
    await interaction.response.send_message(codeblock(repr(cap_l), language="python"))

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
    twitch_streamer_list = d["twitch_streamer_list"]
    tu = parse_twitch_username(twitch_username)
    if tu == None:
        await interaction.response.send_message(code(repr(twitch_username)) + " is not a valid twitch username")
    elif tu.casefold() in (s.casefold() for s in twitch_streamer_list):
        await interaction.response.send_message("Already contains " + plain(recover_case(tu, twitch_streamer_list)))
    elif 100 <= len(twitch_streamer_list):
        await interaction.response.send_message("You can only specify up to 100 names (Twitch API constraint)")
    else:
        twitch_streamer_list.append(tu)
        twitch_streamer_list.sort(key=str.casefold)
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
    cap_l = d["twitch_streamer_list"]
    tu = parse_twitch_username(twitch_username)
    if tu == None:
        await interaction.response.send_message(code(repr(twitch_username)) + " is not a valid twitch username")
    elif tu in cap_l:
        cap_l.remove(tu)
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
    cap_l = d["twitch_category_list"]
    save.save()
    await interaction.response.send_message(codeblock(repr(cap_l), language="python"))

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
        The category to add to the filter.
    """
    if interaction.guild is None: return
    d = save.get_guild_data(str(interaction.guild.id))
    d["name"] = interaction.guild.name
    twitch_category_list = d["twitch_category_list"]
    if twitch_category.casefold() in (c.casefold() for c in twitch_category_list):
        await interaction.response.send_message("Already contains " + plain(recover_case(twitch_category, twitch_category_list)))
    else:
        game_name = None
        try:
            games = api.get_games(names=[twitch_category])
            async for game in games:
                game_name = game.name
                break
        except twitchAPI.type.TwitchBackendException as e:
            print("Twitch API Server Error in twitch-category-add")
            traceback.print_exception(e)
            await interaction.response.send_message("Twitch API Server Error: please try again later")
            return
        if game_name == None:
            await interaction.response.send_message(code(repr(twitch_category)) + " is not a valid twitch category")
        else:
            twitch_category_list.append(game_name)
            twitch_category_list.sort(key=str.casefold)
            save.save()
            await interaction.response.send_message("Added " + plain(game_name))

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
        The category to remove from the filter.
    """
    if interaction.guild is None: return
    d = save.get_guild_data(str(interaction.guild.id))
    d["name"] = interaction.guild.name
    cap_l = d["twitch_category_list"]
    if twitch_category in cap_l:
        cap_l.remove(twitch_category)
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
