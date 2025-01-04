# MatoStreamshow
A discord bot to show live streams

If you want to use the instance of the bot hosted by me, Alex Knauth, contact me on discord.

## Instructions for self-hosting

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
