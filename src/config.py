import json

JSON_PATH = "config.json"

with open(JSON_PATH) as f:
    data: dict = json.load(f)

token: str = data["token"]
twitch_api_id: str | None = data.get("twitch_api_id")
twitch_api_secret: str | None = data.get("twitch_api_secret")

"""
Example config.json:
{
    "token": ""
}
"""
