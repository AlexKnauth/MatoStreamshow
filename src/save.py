import copy, discord, json, os, shutil

JSON_PATH = "save.json"

FULL_TEMPLATE = {
    "guild_template": {
        "name": "",  # Note: automatically set to guild name on addition
        "channel_id": 0,
        "streamer_role_id": 0,
        "live_role_id": 0,
        "twitch_streamer_list": [],
        "twitch_category_list": []
    },
    "guilds": {}
}

data: dict = {}  # Do not access directly - use get_guild_data instead

def save():
    # For write-time safety - if we error mid-write then contents of the file won't be completed!
    if os.path.exists(JSON_PATH):
        shutil.copy2(JSON_PATH, JSON_PATH + ".bak")

    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=4)

def get_guild_ids() -> list[str]:
    return data["guilds"].keys()

def get_guild_data(guild_id: str) -> dict:
    if guild_id not in data["guilds"]:
        print("Guild not found: instantiating")
        init_guild_data(guild_id)
    return data["guilds"][guild_id]

def init_guild_data(guild_id: str):
    data["guilds"][guild_id] = copy.deepcopy(data["guild_template"])
    save()

if not os.path.exists(JSON_PATH):
    data = FULL_TEMPLATE
    save()
else:
    with open(JSON_PATH) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print("Could not deserialise save.json - loading backup")
            with open(JSON_PATH + ".bak") as f2:
                data = json.load(f2)
    save()

def get_lower_set_all() -> set[str]:
    lower_set_all: set[str] = set()
    for g in get_guild_ids():
        d = get_guild_data(g)
        dc_id = d["channel_id"]
        if not (dc_id and dc_id != 0):
            continue
        cap_l = d["twitch_streamer_list"]
        lower_set_all.update((u.casefold() for u in cap_l))
    return lower_set_all
