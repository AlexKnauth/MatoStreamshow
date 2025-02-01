# MatoStreamshow
A discord bot to show live streams

If you want to use the instance of the bot hosted by me, Alex Knauth, contact me on discord.

## Configuring with Commands

Use the `/channel` command to set a channel to post in, for example `/channel #streams-live`.

Use the `/streamer-role` to set a role for it to search for members who are live, and `/live-role` to set a role for it to give members who are live. For example `/streamer-role @VIP` and `/live-role @Now Live`.

You can also use `/twitch-streamer-add` to add twitch usernames, and `/twitch-category-add` to set up a list of categories to filter those twitch usernames by. For example `/twitch-streamer-add AlexKnauth` and `/twitch-category-add Software and Game Development`.

Remove twitch usernames and categories with `/twitch-streamer-remove` and `/twitch-category-remove`, respectively, and see which ones are currently configured with `/twitch-streamer-list` and `/twitch-category-list`, respectively.

## Instructions for Self-hosting

Install the `discordpy` python library with `pip install discord.py`.

Install the `twitchAPI` python library with `pip install twitchAPI`.

Create a `config.json` file,
similar to `templateconfig.json`,
but with the fields filled in:
- token: Discord Bot Token, from the Bot page of your [Discord Developer Portal](https://discord.com/developers/applications)
- twitch_api_id: Client ID from your [Twitch Developer Console](https://dev.twitch.tv/console)
- twitch_api_secret: Client Secret from your [Twitch Developer Console](https://dev.twitch.tv/console) for a Confidential Client

Run:
```bash
python src/MatoStreamshow.py
```

If you get an error message about `ModuleNotFoundError: No module named 'audioop'`,
you can fix that with `pip install audioop-lts`.

## Privacy Policy Questions & Answers

> What data do you collect?

For each Discord Server that the bot connects to, it collects:

- The Server ID / Guild ID of the Discord Server.
- The Server Name.
- The Channel ID of the channel configured by the `/channel` command.
- The Role ID of the streamer role configured by the `/streamer-role` command.
- The Role ID of the live role configured by the `/live-role` command.
- The Twitch Usernames configured by the `/twitch-streamer-add` command.
- The Category / Game names configured by the `/twitch-category-add` command.

And saves that data to a file on the host computer.

It also temporarily collects:
- The message history of the channel configured by the `/channel` command, going back 100 messages.
- The list of server members who have the streamer role configured by the `/streamer-role` command.
- The activities of those server members with the streamer role, including:
  - Twitch Username and URL
  - Stream Title
  - Stream Category / Game
  - Stream Thumbnail URL

And posts messages containing this information to the Discord Server in the channel configured by the `/channel` command.

If something goes wrong with the bot,
error messages containing this temporary data may be logged on the host computer for debugging,
but otherwise during normal operations,
this temporary data is not stored.

> Why do you need the data?

All the data except for the Server Name is necessary for the function of the bot.

The Server Name is not strictly necessary,
but it is nice to have in case something goes wrong with the bot in one particular Discord Server.
If the host ever needs to look into the data manually to see what might be wrong or correct it,
the Server Name helps the host know where to look.

The Server ID and Channel ID are neccesary for the bot to know where to post messages.
The message history of the channel is neccesary for the bot to delete or edit its own potentially out-of-date messages,
including potentially out-of-date messages posted by a previous instance of the bot on the other side of a restart.
The Role IDs, Twitch Usernames, Server Members, and Activities are neccesary for the bot to check who is live, and what role to give them when they are live.
The Twitch Category / Game Names are necessary for the bot to filter live streams by category.

> How do you use the data?

The bot uses the data to post messages in the channel configured by the `/channel` command.
The host may use the data to help debug or improve the bot.

> Other than Discord the company and users of your own bot, who do you share your collected data with?

The host may share the data with anyone that the host believes might help them debug or improve the bot.

> How can users contact you with concerns?

If you're using the instance of the bot hosted by me, Alex Knauth,
then you can contact me on Discord, or through the
[Github Issues](https://github.com/AlexKnauth/MatoStreamshow/issues)
page of this repository.

> How can users have that data removed?

Twitch Usernames can be removed with the `/twitch-streamer-remove` command.

Twitch Category / Game Names can be removed with the `/twitch-category-remove` command.

Even after removing data with those commands,
the data may persist in backup files,
and backup files may be used if something goes wrong with the main files.
