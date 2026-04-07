import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from copy import deepcopy as copy
# from copy import copy as copy
from twitchAPI.twitch import Twitch
from twitchAPI.object.api import TwitchUser
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.oauth import UserAuthenticationStorageHelper
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, NoticeEvent, WhisperEvent, JoinEvent, LeftEvent   # , ChatCommand


def get_data_path() -> Path:
    FOLDER_NAME = "DuckStuff"
    if getattr(sys, 'frozen', False):
        if sys.platform == "win32":
            try:
                from ctypes import windll, create_unicode_buffer
                buf = create_unicode_buffer(260)
                # noinspection PyUnresolvedReferences
                if windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
                    base = Path(buf.value)
                else:
                    base = Path(os.environ["USERPROFILE"]) / "Documents"
            except Exception as e:
                logger.error(f"{fortime()}: Error in 'get_data_path' -- {e}")
                base = Path(os.environ["USERPROFILE"]) / "Documents"
        else:
            base = Path.home() / "Documents"
        return base / FOLDER_NAME
    else:
        return Path(__file__).parent


DATA_PATH = get_data_path()
DIRECTORIES = {
    "auth": DATA_PATH / "auth",
    "data": DATA_PATH / "data",
    "stream": DATA_PATH / "data" / "stream",
    "stream_archive": DATA_PATH / ".archived" / "data" / "stream",
    "logs": DATA_PATH / "logs",
    "logs_archive": DATA_PATH / ".archived" / "logs"
}

for path in DIRECTORIES.values():
    path.mkdir(parents=True, exist_ok=True)

AUTH_JSON = DIRECTORIES['auth'] / "auth_info.json"
TWITCH_TOKEN = DIRECTORIES['auth'] / "twitch_token.json"
BOT_NAMES = [
    "streamelements",
    "sery_bot",
    "tangiabot"
]
BLANK_STREAM_DATA = {
    "data": {
        "bits": 0,
        "chat_msg_count": 0,
        "chatters_new": 0,
        "raids": {
            "total": 0,
            "viewers": 0
        },
        "subbies_gifted": 0,
        "subbies_new": 0,
        "subbies_renewed": 0,
        "viewers_avg": 0,
        "viewers_max": 0,
        "viewers_min": 0
    },
    "info": {
        "streamer": None,
        "time": {
            "ended": None,
            "started": None
            }
}
}
EMOTES = {
            "flag": {
                "roll": "therav27FlagRoll"
            },
            "hype": {
                "parrot": "therav27ParrotHYPE",
                "skelly": "therav27SKELLYDANCE"
            },
            "raid": {
                "rave": "therav27RaidRave"
            }
        }
FORMAT_TIME = "%Y-%m-%d--%H-%M-%S"
HYPE = "!hyp"

log_list = []
users_in_chat = {}
data_stream_timestamp = 0


# ----------------- Class Setup ----------------- #
class BotSetup(Twitch):
    def __init__(self, app_id: str, app_secret: str):
        super().__init__(app_id, app_secret)
        self.bot = Twitch
        self.target_rooms = [
            "theravenarmed"
            # "theechody"
            # "xboxbaldmara"
        ]
        self.target_scopes = [
            AuthScope.CHANNEL_BOT,
            AuthScope.CHANNEL_READ_SUBSCRIPTIONS,
            AuthScope.CHAT_READ,
            AuthScope.CHAT_EDIT,
            AuthScope.USER_BOT,
            AuthScope.USER_READ_CHAT,
            AuthScope.USER_WRITE_CHAT,
            AuthScope.WHISPERS_READ
        ]

    @staticmethod
    async def invalid_input() -> None:
        print("Invalid input, try again...")
        await asyncio.sleep(2)

    @staticmethod
    def long_dashes() -> str:
        return "-" * os.get_terminal_size().columns


# ----------------- BOT FUNCTIONS ----------------- #
async def auth_bot() -> None:
    twitch_helper = UserAuthenticationStorageHelper(bot, bot.target_scopes, TWITCH_TOKEN)
    await twitch_helper.bind()
    logger.info(f"{fortime()}: Bot Authenticated Successfully!\n{bot.long_dashes()}")


def check_db_auth() -> dict | None:
    def fetch_stock_auth() -> dict | None:
        return {
            "bot_id": None,
            "secret_id": None,
            "db_string": None
        }

    if not os.path.exists(AUTH_JSON):
        save_json(fetch_stock_auth(), AUTH_JSON)
    _auth_dict = read_file(AUTH_JSON, {"json": True})
    if None in (_auth_dict['bot_id'], _auth_dict['secret_id']):
        _auth_dict = update_auth_json(_auth_dict)
    return _auth_dict


def create_new_data_stream() -> dict:
    _data_stream = copy(BLANK_STREAM_DATA)
    return _data_stream


def cls() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def fetch_data_stream(_data_stream_timestamp: float) -> tuple[dict, float]:
    date_form_current = datetime.now()
    for _, __, files in os.walk(DIRECTORIES['stream']):
        for filename in files:
            if filename.endswith(".json"):
                try:
                    date_form = datetime.strptime(filename.replace('.json', ''), FORMAT_TIME)
                    if date_form_current.timestamp() - date_form.timestamp() < (3600 * 6):
                        _data_stream_timestamp = date_form.timestamp()
                        return read_file(DIRECTORIES['stream'] / filename, {"json": True}), _data_stream_timestamp
                    else:
                        try:
                            os.rename(DIRECTORIES['stream'] / filename, DIRECTORIES['stream_archive'] / filename)
                        except Exception as _error:
                            logger.error(f"{fortime()}: Error in 'fetch_data_stream' -- Moving {filename} to archives -- {_error}")
                            continue
                except Exception as _error:
                    logger.error(f"{fortime()}: ERROR in 'fetch_data_stream' -- {_error}")
                    return create_new_data_stream(), _data_stream_timestamp
    return create_new_data_stream(), _data_stream_timestamp


def fetch_users() -> str:
    return f"{len(users_in_chat[bot.target_rooms[0]]):,}"


def fortime() -> str:
    return datetime.now().strftime('%y-%m-%d %H:%M:%S')


async def get_auth_user_id() -> None | TwitchUser:
    user_info = bot.get_users()
    try:
        async for entry in user_info:
            if type(entry) == TwitchUser:
                _user = entry
                return _user
            else:
                logger.error(f"{fortime()}: NO USER FOUND IN 'user_info'")
                return None
    except Exception as _error:
        logger.error(f"{fortime()}: {_error}")
        return None


def get_max_length(keys: list) -> int:
    l = 0
    for key in keys:
        if len(key) > l:
            l = len(key)
    return l


def print_max_length(_str: str, length: int) -> str:
    return f"{_str}{' ' * (length - len(_str))}"


def print_stream_stats(stream_stats: dict) -> None:
    length = get_max_length(list(stream_stats.keys()))
    sorted_stats = dict(sorted(stream_stats.items()))
    for key, value in sorted_stats.items():
        print(f"{print_max_length(key.replace('_', ' ').title(), length)}: {value}")


def read_file(file_name: Path | str, return_type: bool | dict | float | int | list | str) -> bool | dict | float | int | list | None | str:
    def open_file(json_: bool = False):
        with open(file_name, "r", encoding="utf-8") as file:
            if json_:
                return json.load(file)
            else:
                return file.read()

    try:
        if return_type == bool:
            variable = open_file()
            if variable == "True":
                return True
            elif variable == "False":
                return False
            else:
                return f"ValueError Converting {variable} to {return_type}"
        elif type(return_type) == dict:
            if return_type['json']:
                return open_file(True)
            else:
                return dict(open_file())
        elif return_type == dict:
            return dict(open_file())
        elif type(return_type) == list:
            variable = open_file()
            if return_type[1] == "split":
                variable = variable.split(return_type[2], maxsplit=return_type[3])
            elif return_type[1] == "splitlines":
                variable = variable.splitlines()
            if return_type[0] == map:
                return list(map(str, variable))
            else:
                return list(variable)
        elif return_type in (int, float):
            variable = float(open_file())
            if return_type == float:
                return variable
            return int(variable)
        else:
            return open_file()
    except FileNotFoundError:
        logger.error(f"{fortime()}: {file_name} Doesn't Exist!")
        time.sleep(5)
        return None
    except ValueError:
        variable = open_file()
        return f"ValueError Converting {variable} (type; {type(variable)}) to {return_type}"
    except Exception as _error:
        error_msg = f"{fortime()}: Error in 'read_file' -- Generic Error -- {_error}"
        logger.error(error_msg)
        time.sleep(5)
        return error_msg


def save_data_stream(_data: dict, file_save: str) -> None:
    _data['info']['time']['ended'] = datetime.strftime(datetime.now(), FORMAT_TIME)
    save_json(_data, DIRECTORIES['stream'] / file_save)


def save_json(_data: dict, file_save: Path | str) -> None:
    if _data is None:
        logger.error(f"{fortime()}: _data is None!!!")
        return
    with open(file_save, "w", encoding="utf-8") as file:
        json.dump(_data, file, indent=4, ensure_ascii=False)


def shutdown_logger(_log_list: list) -> None:
    logging.shutdown()
    for entry in _log_list:
        try:
            os.rename(DIRECTORIES['logs'] / entry, DIRECTORIES['logs_archive'] / entry)
            print(f"{entry} moved to archives..")
        except Exception as _error:
            print(_error)
            time.sleep(10)
            pass


def setup_logger(name: str, log_file: str, _log_list: list, level=logging.INFO) -> logging.Logger | None:
    try:
        local_logger = logging.getLogger(name)
        handler = logging.FileHandler(Path(DIRECTORIES['logs'] / log_file), mode="w", encoding="utf-8")
        if name == "logger":
            console_handler = logging.StreamHandler()
            local_logger.addHandler(console_handler)
        local_logger.setLevel(level)
        local_logger.addHandler(handler)
        _log_list.append(log_file)
        return local_logger
    except Exception as _error:
        print(f"{fortime()}: ERROR in setup_logger - {name}/{log_file}/{level} -- {_error}")
        time.sleep(15)
        _log_list.append(None)
        return None


def subbie_tier_check(raw_tier: str) -> str:
    if raw_tier == "1000":
        return "Tier 1"
    elif raw_tier == "2000":
        return "Tier 2"
    else:
        return "Tier 3"


def total_subbies() -> int:
    return data_stream['data']['subbies_gifted'] + data_stream['data']['subbies_new'] + data_stream['data']['subbies_renewed']


def update_auth_json(current_dict: dict) -> dict:
    while True:
        cls()
        _user_input = input("Enter In Client ID\n")
        if _user_input == "":
            print("Invalid Input, try again")
            time.sleep(2)
        else:
            current_dict['bot_id'] = _user_input
            print(f"Setting '{current_dict['bot_id']}' as thee Client ID")
            time.sleep(2)
            break
    while True:
        cls()
        _user_input = input("Enter In Secret ID\n")
        if _user_input == "":
            print("Invalid Input, try again")
            time.sleep(2)
        else:
            current_dict['secret_id'] = _user_input
            print(f"Setting '{current_dict['secret_id']}' as thee Secret ID")
            time.sleep(2)
            break
    save_json(current_dict, AUTH_JSON)
    return current_dict


# ----------------- MAIN_BOT_FUNCTIONS ----------------- #
async def on_message(msg: ChatMessage) -> None:
    try:
        if msg.user.name != bot.target_rooms[0] and msg.user.name not in BOT_NAMES:
            data_stream['data']['chat_msg_count'] += 1
        time_ = fortime()
        logger_chat.info(f"{time_}: {msg.user.id}|{msg.user.display_name}; {msg.text}")
        logger_test.info(f"{time_}: text; {msg.text}\nhype chat; {msg.hype_chat}\nbits; {msg.bits}\nemotes; {msg.emotes}\nfirst; {msg.first}\n")
        if msg.bits > 0:
            data_stream['data']['bits'] += msg.bits
            logger_sim.info(f"{HYPE} {msg.user.display_name} for cheering {msg.bits:,} bits!!")
        elif msg.first:
            data_stream['data']['chatters_new'] += 1
            logger_sim.info(f"Welcome aboard @{msg.user.display_name}")
        elif msg.user.name == bot.target_rooms[0] and "gifting" in msg.text:
            username, text = msg.text.split(" just earned ")
            _, number_subs = text.split(" Shillings for gifting ")
            number_subs, _ = number_subs.split(" subscription")
            if number_subs.isdigit():
                number_subs = int(number_subs)
            elif number_subs == "a":
                number_subs = 1
            else:
                logger.error(f"{fortime()}: Error in 'on_message/elif msg.user.name == bot.target_rooms[0]/number_subs can't be figured' -- {number_subs}")
                number_subs = 0
            data_stream['data']['subbies_gifted'] += number_subs
            logger_sim.info(f"{HYPE} {username} for the {number_subs:,} GIFT SUBS!")
    except Exception as _error:
        logger.error(f"{fortime()}: ERROR 'on_message' - {_error}")
        return


async def on_notice(event: NoticeEvent) -> None:
    try:
        logger_notice.info(f"{fortime()}: {type(event)}\nid; {event.msg_id}\nmessage; {event.message}\n")
    except Exception as _error:
        logger.error(f"{fortime()}: ERROR 'on_notice' - {_error}")
        return


async def on_raid(event: dict) -> None:
    try:
        logger_raid.info(f"{fortime()}: {type(event)}\n{event}\n")
        for key, value in event.items():
            logger_raid.info(f"{fortime()}: {key}; {value}")
        logger_raid.info("")

        raider_channel = event['tags']['msg-param-displayName']
        raiders_number = event['tags']['msg-param-viewerCount']
        raiders_number = int(raiders_number)
        data_stream['data']['raids']['total'] += 1
        data_stream['data']['raids']['viewers'] += raiders_number
        logger_sim.info(f"{EMOTES['raid']['rave']} {EMOTES['hype']['parrot']} {EMOTES['hype']['skelly']} {EMOTES['flag']['roll']} WELCOME TO THE CREW {raiders_number:,} RAIDERS OF {raider_channel} {EMOTES['flag']['roll']} {EMOTES['hype']['skelly']} {EMOTES['hype']['parrot']} {EMOTES['raid']['rave']}")
    except Exception as _error:
        logger.error(f"{fortime()}: ERROR 'on_raid' - {_error}")
        return


async def on_ready(event: EventData) -> None:
    try:
        for username in bot.target_rooms:
            await event.chat.join_room(username)
            users_in_chat[username] = [user.login]
            logger.info(f"{fortime()}: Joined {username} chat!")
    except Exception as _error:
        logger.error(f"{fortime()}: ERROR 'on_ready' - {_error}")
        return


async def on_sub(sub: ChatSub) -> None:
    try:
        time_ = fortime()
        logger_sub.info(f"{time_}: {type(sub)}\n{sub}\n")
        logger_sub.info(f"{time_}: sub plan; {sub.sub_plan}\nsub plan name; {sub.sub_plan_name}\nsub type; {sub.sub_type}\nsub msg; {sub.sub_message}\nsys msg; {sub.system_message}")
        try:
            if sub.sub_type == "sub":
                logger.info(f"{time_}: NEWSUB\nNEWSUB\nNEWSUB\nNEWSUB\nNEWSUB\nNEWSUB\nNEWSUB\nNEWSUB\n")
                logger_sub.info(f"{time_}: NEWSUB\nNEWSUB\nNEWSUB\nNEWSUB\nNEWSUB\nNEWSUB\nNEWSUB\nNEWSUB\n")
        except Exception as _error:
            logger.error(f"{fortime()}: Error in 'on_sub/sub' -- {_error}")
            return
        if sub.sub_type == "resub":
            try:
                streak_sub_time = 0
                system_msg = sub.system_message.split("\\", maxsplit=16)
                username = system_msg[0]
                sub_tier = system_msg[4].lstrip("s").rstrip(".")
                total_sub_time = int(system_msg[8].lstrip("s"))
                if len(system_msg) > 10:
                    streak_sub_time = int(system_msg[13].lstrip("s"))
                data_stream['data']['subbies_resub'] += 1
                logger_sim.info(f"{HYPE} @{username} for the T{sub_tier} RESUB!!{f" @{username} has been subbed for {total_sub_time:,} Months{f", currently on a {streak_sub_time} Streak!!" if streak_sub_time > 0 else "!!"}" if total_sub_time > 0 else ""}")
            except Exception as _error:
                logger.error(f"{fortime()}: ERROR 'on_sub/resub' - {_error}")
                return
    except Exception as _error:
        logger.error(f"{fortime()}: ERROR 'on_sub' - {_error}")
        return


async def on_user_join(event: JoinEvent) -> None:
    try:
        chatter_name = event.user_name
        streamer_name = event.room.name
        if chatter_name == streamer_name or chatter_name in BOT_NAMES:
            return
        elif chatter_name not in users_in_chat[streamer_name]:
            users_in_chat[streamer_name].append(chatter_name)
            logger_viewers.info(f"{fortime()}: {chatter_name} has joined the chat! {len(users_in_chat[streamer_name])} viewers present!")
    except Exception as _error:
        logger.error(f"{fortime()}: ERROR 'on_user_join' - {_error}")
        return


async def on_user_left(event: LeftEvent) -> None:
    try:
        chatter_name = event.user_name
        streamer_name = event.room_name
        if chatter_name == streamer_name or chatter_name in BOT_NAMES:
            return
        elif chatter_name in users_in_chat[streamer_name]:
            users_in_chat[streamer_name].remove(chatter_name)
            logger_viewers.info(f"{fortime()}: {event.user_name} has left the chat! {len(users_in_chat[streamer_name])} viewers present!")
    except Exception as _error:
        logger.error(f"{fortime()}: ERROR 'on_user_left' - {_error}")
        return


async def on_whisper(event: WhisperEvent) -> None:
    try:
        logger_whisper.info(f"{fortime()}: {event.message}")
    except Exception as _error:
        logger.error(f"{fortime()}: ERROR 'on_whisper' - {_error}")
        return


# ----------------- MAIN_BOT_LOOP ----------------- #
async def run() -> None:
    async def shutdown():
        chat.stop()
        logger.info(f"{bot.long_dashes()}\n{fortime()}: Chat Stopped!\n{bot.long_dashes()}")
        await asyncio.sleep(1)
        await bot.close()
        logger.info(f"{fortime()}: Bot Closed!\n{bot.long_dashes()}")
        await asyncio.sleep(1)

    chat = await Chat(bot)
    chat.register_event(ChatEvent.READY, on_ready)
    chat.register_event(ChatEvent.MESSAGE, on_message)
    chat.register_event(ChatEvent.SUB, on_sub)
    chat.register_event(ChatEvent.RAID, on_raid)
    chat.register_event(ChatEvent.NOTICE, on_notice)
    chat.register_event(ChatEvent.WHISPER, on_whisper)
    chat.register_event(ChatEvent.JOIN, on_user_join)
    chat.register_event(ChatEvent.USER_LEFT, on_user_left)
    chat.start()

    await asyncio.sleep(1.5)
    while True:
        cls()
        save_data_stream(data_stream, SAVE_FILE)
        try:
            try:
                stream_stats = {
                    "viewers": fetch_users(),
                    "chat_msg_count": f"{data_stream['data']['chat_msg_count']:,}",
                    "chat_new_viewer": f"{data_stream['data']['chatters_new']:,}",
                    "bits": f"{data_stream['data']['bits']:,}",
                    "subbies_total": f"{total_subbies():,}",
                    "subbies_gifted": f"{data_stream['data']['subbies_gifted']:,}",
                    "subbies_new": f"{data_stream['data']['subbies_new']:,}",
                    "subbies_renewed": f"{data_stream['data']['subbies_renewed']:,}",
                    "raids": f"{data_stream['data']['raids']['total']:,}/{data_stream['data']['raids']['viewers']:,}"
                }
                print_stream_stats(stream_stats)
            except Exception as _error:
                logger.error(f"{fortime()}: ERROR 'on_stream_stats' - {_error}")
                pass
            user_input = input(f"{bot.long_dashes()}\n"
                               f"Enter 1 To View Names of Users\n"
                               f"Enter 0 To Exit\n")
            if user_input == "":
                pass
            elif user_input.isdigit():
                user_input = int(user_input)
                if user_input == 0:
                    break
                elif user_input == 1:
                    cls()
                    for username in sorted(users_in_chat[bot.target_rooms[0]]):
                        print(username)
                    print(f"{bot.long_dashes()}\nTotal; {fetch_users()}")
                    input("Hit enter to continue...")
                elif user_input == 69:
                    input("haha, funny sex number")
                elif user_input == 183:
                    await bot.invalid_input()
                elif user_input == 420:
                    await bot.invalid_input()
                else:
                    await bot.invalid_input()
            else:
                await bot.invalid_input()
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"{fortime()}: Error in bot loop -- {e}")
            try:
                continue
            except Exception as ee:
                logger.error(f"{fortime()}: Error continuing from last error -- {ee}")
                await asyncio.sleep(2)
                break

    await shutdown()


if __name__ == "__main__":
    def shutdown():
        save_data_stream(data_stream, SAVE_FILE)
        logger.info(f"{fortime()}: '{SAVE_FILE}' saved!")
        shutdown_logger(log_list)
        cls()
        sys.exit(0)

    init_time = datetime.now().strftime(FORMAT_TIME)
    logger = setup_logger("logger", f"main_log--{init_time}.log", log_list)
    logger_chat = setup_logger("logger_chat", f"chat_log--{init_time}.log", log_list)
    logger_notice = setup_logger("logger_notice", f"notice_log--{init_time}.log", log_list)
    logger_raid = setup_logger("logger_raid", f"raid_log--{init_time}.log", log_list)
    logger_sub = setup_logger("logger_sub", f"sub_log--{init_time}.log", log_list)
    logger_sim = setup_logger("logger_sim", f"sim_log--{init_time}.log", log_list)
    logger_test = setup_logger("logger_test", f"test_log--{init_time}.log", log_list)
    logger_viewers = setup_logger("logger_viewers", f"viewers_log--{init_time}.log", log_list)
    logger_whisper = setup_logger("logger_whisper", f"whisper_log--{init_time}.log", log_list)


    if None in log_list:
        print(f"One or more logger files not set up right\n{log_list}")
        print("Shutting down in 30 seconds")
        time.sleep(30)
        shutdown()

    try:
        auth_dict = check_db_auth()
        if auth_dict is not None:
            bot = BotSetup(auth_dict['bot_id'], auth_dict['secret_id'])
            asyncio.run(auth_bot())
            user = asyncio.run(get_auth_user_id())
            if user is not None:
                data_stream, data_stream_timestamp = fetch_data_stream(data_stream_timestamp)
                SAVE_FILE = f"{init_time if data_stream_timestamp == 0 else datetime.strftime(datetime.fromtimestamp(data_stream_timestamp), FORMAT_TIME)}.json"
                if data_stream['info']['streamer'] is None:
                    data_stream['info']['streamer'] = bot.target_rooms[0]
                if data_stream['info']['time']['started'] is None:
                    data_stream['info']['time']['started'] = datetime.strftime(datetime.fromtimestamp(data_stream_timestamp), FORMAT_TIME)
                asyncio.run(run())
        shutdown()
    except KeyboardInterrupt:
        shutdown()
    except Exception as e:
        logger.error(f"{fortime()}: Error in main loop -- {e}")
