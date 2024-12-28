import json

JSON_PATH = "config.json"

with open(JSON_PATH) as f:
    data: dict = json.load(f)

token: str = data["token"]

"""
Example config.json:
{
    "token" : ""
}
"""
