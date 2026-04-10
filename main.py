from __future__ import annotations
import os
import sys
import json
import time
import asyncio
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from copy import deepcopy as copy
from twitchAPI.twitch import Twitch
from typing import Literal, overload
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
BOT_NAMES = (
    "fossabot",
    "moobot",
    "nightbot",
    "pokemoncommunitygame",
    "sery_bot",
    "soundalerts",
    "streamelements",
    "streamlabs",
    "streamlootsbot",
    "streamstickers",
    "tangiabot",
    "wizebot"
)
BLANK_STREAM_DATA = {
    "data": {
        "bits": 0,
        "chat_msg_count": 0,
        "chatters_new": 0,
        "raids": {
            "total": 0,
            "viewers": 0
        },
        "subbies": {
            "gifted": 0,
            "new": 0,
            "resub": 0
        },
        "viewers": {
            "avg": 0,
            "max": 0,
            "min": 0
        }
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
SAVE_FILE_INIT = False

log_list = []
users_in_chat = {}
data_stream_timestamp = 0


# ----------------- Class Setup ----------------- #
class BotSetup(Twitch):
    def __init__(self, app_id: str, app_secret: str):
        super().__init__(app_id, app_secret)
        self.bot = Twitch
        self.target_room = [
            # "theravenarmed"
            # "theechody"
            "xboxbaldmara"
            # "piousduck83"
            # "rocker_joe"
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


class DictOptions:
    __slots__ = ("json",)

    def __init__(self, json: bool = False):
        self.json = json


class ListOptions:
    __slots__ = ("mode", "sep", "maxsplit", "cast_map")

    def __init__(
        self,
        mode: Literal["split", "splitlines", "none"] = "none",
        sep: str = "",
        maxsplit: int = -1,
        cast_map: bool = False,
    ):
        self.mode = mode
        self.sep = sep
        self.maxsplit = maxsplit
        self.cast_map = cast_map


# ----------------- OVERLOADS ----------------- #
@overload
def read_file(file_name: Path | str, return_type: type[bool]) -> bool | str: ...
@overload
def read_file(file_name: Path | str, return_type: type[dict] | DictOptions) -> dict: ...
@overload
def read_file(file_name: Path | str, return_type: type[float]) -> float: ...
@overload
def read_file(file_name: Path | str, return_type: type[int]) -> int: ...
@overload
def read_file(file_name: Path | str, return_type: type[list] | ListOptions) -> list: ...
@overload
def read_file(file_name: Path | str, return_type: type[str]) -> str: ...
@overload
async def get_auth_user_id() -> TwitchUser: ...
@overload
async def get_auth_user_id() -> TwitchUser: ...


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
    _auth_dict = read_file(AUTH_JSON, DictOptions(json=True))
    if None in (_auth_dict['bot_id'], _auth_dict['secret_id']):
        _auth_dict = update_auth_json(_auth_dict)
    return _auth_dict


def create_new_data_stream() -> dict:
    _data_stream = copy(BLANK_STREAM_DATA)
    return _data_stream


def clear() -> None:
    subprocess.run(['cls' if os.name == 'nt' else 'clear'], shell=(os.name == 'nt'))



def fetch_data_stream(_data_stream_timestamp: float) -> tuple[dict, float]:
    date_form_current = datetime.now()
    for _, __, files in os.walk(DIRECTORIES['stream']):
        for filename in files:
            if filename.endswith(".json"):
                try:
                    date_form = datetime.strptime(filename.replace('.json', ''), FORMAT_TIME)
                    if date_form_current.timestamp() - date_form.timestamp() < (3600 * 6):
                        _data_stream_timestamp = date_form.timestamp()
                        _data_stream = read_file(DIRECTORIES['stream'] / filename, return_type=DictOptions(json=True))
                        if _data_stream['info']['streamer'] == bot.target_room[0]:
                            return _data_stream, _data_stream_timestamp
                        else:
                            move_file(DIRECTORIES['stream'] / filename, DIRECTORIES['stream_archive'] / filename)
                    else:
                        move_file(DIRECTORIES['stream'] / filename, DIRECTORIES['stream_archive'] / filename)
                except Exception as _error:
                    logger.error(f"{fortime()}: ERROR in 'fetch_data_stream' -- {_error}")
                    return create_new_data_stream(), _data_stream_timestamp
    return create_new_data_stream(), _data_stream_timestamp


def fortime() -> str:
    return datetime.now().strftime('%y-%m-%d %H:%M:%S')


async def get_auth_user_id():
    user_info = bot.get_users()
    try:
        async for entry in user_info:
            if isinstance(entry, TwitchUser):
                return entry
            else:
                logger.error(f"{fortime()}: NO USER FOUND IN 'user_info'")
                exit()
    except Exception as _error:
        logger.error(f"{fortime()}: {_error}")
        exit()


def get_max_length(keys: list) -> int:
    l = 0
    for key in keys:
        if len(key) > l:
            l = len(key)
    return l


def move_file(old_path: Path, new_path: Path) -> None:
    try:
        os.rename(old_path, new_path)
    except Exception as _error:
        logger.error(f"{fortime()}: Error in 'fetch_data_stream' -- Moving {old_path} to {new_path} -- {_error}")


def print_max_length(_str: str, length: int) -> str:
    return f"{_str}{' ' * (length - len(_str))}"


def print_stream_stats(stream_stats: dict) -> None:
    length = get_max_length(list(stream_stats.keys()))
    sorted_stats = dict(sorted(stream_stats.items()))
    for key, value in sorted_stats.items():
        print(f"{print_max_length(key.replace('_', ' ').replace('-', '/').title(), length)}: {value}")


def read_file(file_name: Path | str,
              return_type: type[bool | dict | float | int | list | str] | ListOptions | DictOptions
              ) -> bool | dict | float | int | list | str | None:

    def open_file(json_: bool = False) -> str | dict:
        with open(file_name, "r", encoding="utf-8") as file:
            return json.load(file) if json_ else file.read()

    try:
        # --- bool ---
        if return_type is bool:
            raw = open_file()
            if raw == "True":
                return True
            elif raw == "False":
                return False
            return f"ValueError Converting {raw!r} to {return_type}"

        # --- dict (with options) ---
        if isinstance(return_type, DictOptions):
            return open_file(return_type.json)  # type: ignore[return-value]
        if return_type is dict:
            return dict(open_file())  # type: ignore[call-overload]

        # --- list (with options) ---
        if isinstance(return_type, ListOptions):
            raw = open_file()
            assert isinstance(raw, str)
            raw = open_file()
            assert isinstance(raw, str)
            if return_type.mode == "split":
                parts = raw.split(return_type.sep, maxsplit=return_type.maxsplit)
            elif return_type.mode == "splitlines":
                parts = raw.splitlines()
            else:
                parts = list(raw)
            return list(map(str, parts)) if return_type.cast_map else parts
        if return_type is list:
            return list(open_file())

        if return_type is int:
            return int(float(open_file()))  # type: ignore[arg-type]
        if return_type is float:
            return float(open_file())       # type: ignore[arg-type]

        return open_file()  # type: ignore[return-value]

    except FileNotFoundError:
        logger.error(f"{fortime()}: {file_name} Doesn't Exist!")
        time.sleep(5)
        return None
    except ValueError:
        raw = open_file()
        return f"ValueError Converting {raw!r} (type: {type(raw)}) to {return_type}"
    except Exception as _error:
        error_msg = f"{fortime()}: Error in 'read_file' -- Generic Error -- {_error}"
        logger.error(error_msg)
        time.sleep(5)
        return error_msg


def save_data_stream(_data: dict, file_save: str) -> None:
    _data = viewers_update(_data)
    _data['info']['time']['ended'] = datetime.strftime(datetime.now(), FORMAT_TIME)
    save_json(_data, DIRECTORIES['stream'] / file_save)


def save_json(_data: dict | None, file_save: Path | str) -> None:
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
            time.sleep(5)
            continue


def setup_logger(name: str, log_file: str, _log_list: list, level=logging.INFO) -> logging.Logger:
    try:
        local_logger = logging.getLogger(name)
        handler = logging.FileHandler(DIRECTORIES['logs'] / log_file, mode="w", encoding="utf-8")
        if name == "logger":
            console_handler = logging.StreamHandler()
            local_logger.addHandler(console_handler)
        local_logger.setLevel(level)
        local_logger.addHandler(handler)
        _log_list.append(log_file)
        return local_logger
    except Exception as _error:
        print(f"{fortime()}: ERROR in setup_logger - {name}/{log_file}/{level} -- {_error}\n{bot.long_dashes()}")
        print(f"This Window Will Close In 60 Seconds, Copy Above And Paste Into Text Editor!\n{bot.long_dashes()}")
        time.sleep(60)
        exit()


def subbie_tier_check(raw_tier: str) -> str:
    if raw_tier == "Prime":
        return "Prime"
    elif raw_tier == "1000":
        return "Tier 1"
    elif raw_tier == "2000":
        return "Tier 2"
    else:
        return "Tier 3"


def total_subbies() -> int:
    return data_stream['data']['subbies']['gifted'] + data_stream['data']['subbies']['new'] + data_stream['data']['subbies']['resub']


def update_auth_json(current_dict: dict) -> dict:
    while True:
        clear()
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
        clear()
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


def viewers_fetch_current() -> int:
    return len(users_in_chat[bot.target_room[0]])


def viewers_update(_data: dict) -> dict:
    viewers_current = viewers_fetch_current()
    if datetime.now().timestamp() - datetime.strptime(_data['info']['time']['started'], FORMAT_TIME).timestamp() < 900:
        _data['data']['viewers']['min'] = viewers_current if viewers_current > _data['data']['viewers']['min'] else _data['data']['viewers']['min']
    else:
        _data['data']['viewers']['min'] = _data['data']['viewers']['min'] if _data['data']['viewers']['min'] < viewers_current else viewers_current
    _data['data']['viewers']['max'] = _data['data']['viewers']['max'] if _data['data']['viewers']['max'] > viewers_current else viewers_current
    return _data


# ----------------- MAIN_BOT_FUNCTIONS ----------------- #
async def on_message(msg: ChatMessage) -> None:
    try:
        if msg.user.name in BOT_NAMES:
            return
        if msg.user.name != bot.target_room[0]:
            _time = fortime()
            data_stream['data']['chat_msg_count'] += 1
            logger_chat.info(f"{_time}: {msg.user.id}|{msg.user.display_name}; {msg.text}")
            logger_test.info(f"{_time}: text; {msg.text}\nhype chat; {msg.hype_chat}\nbits; {msg.bits}\nemotes; {msg.emotes}\nfirst; {msg.first}\nis_me; {msg.is_me}")
            if msg.bits > 0:
                data_stream['data']['bits'] += msg.bits
                logger_sim.info(f"{HYPE} {msg.user.display_name} for cheering {msg.bits:,} bits!!")
            elif msg.first:
                data_stream['data']['chatters_new'] += 1
                logger_sim.info(f"Welcome aboard {msg.user.display_name}")
        elif msg.user.name == "theravenarmed" and "gifting" in msg.text:
            username, text = msg.text.split(" just earned ")
            _, number_subs = text.split(" Shillings for gifting ")
            number_subs, _ = number_subs.split(" subscription")
            if number_subs.isdigit():
                number_subs = int(number_subs)
            elif number_subs == "a":
                number_subs = 1
            else:
                logger.error(f"{fortime()}: Error in 'on_message/elif msg.user.name == bot.target_room[0]/number_subs can't be figured' -- {number_subs}")
                number_subs = 0
            data_stream['data']['subbies']['gifted'] += number_subs
            logger_sim.info(f"{HYPE} {username} for the {number_subs:,} GIFT SUB{"S" if number_subs > 1 else ""}!")
    except Exception as _error:
        logger.error(f"{fortime()}: ERROR 'on_message' - {_error}")
        return


async def on_notice(event: NoticeEvent) -> None:
    try:
        _time = fortime()
        logger_notice.info(f"{_time}: {type(event)}\nid; {event.msg_id}\nmessage; {event.message}\n")
        logger.info(f"{_time}: NOTICE_EVENT")
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
        username = bot.target_room[0]
        await event.chat.join_room(username)
        users_in_chat[username] = [user.login]
        logger.info(f"{fortime()}: Joined {username} chat!\n{bot.long_dashes()}")
    except Exception as _error:
        logger.error(f"{fortime()}: ERROR 'on_ready' - {_error}")
        return


async def on_sub(sub: ChatSub) -> None:
    try:
        _time = fortime()
        logger_sub.info(f"{_time}: {type(sub)}\n{sub}\n")
        logger_sub.info(f"{_time}: sub plan; {sub.sub_plan}\nsub plan name; {sub.sub_plan_name}\nsub type; {sub.sub_type}\nsub msg; {sub.sub_message}\nsys msg; {sub.system_message}")
        if sub.sub_type == "sub":
            data_stream['data']['subbies']['new'] += 1
            logger_sim.info(f"{HYPE} {sub.system_message.split('\\')[0]} for the BRAND NEW {subbie_tier_check(sub.sub_plan).capitalize()} SUB!!")
        if sub.sub_type == "resub":
            try:
                data_stream['data']['subbies']['resub'] += 1
                # sub_plan_name = sub.sub_plan_name
                # sub_msg = sub.sub_message.split("\\", maxsplit=9)
                sys_msg = sub.system_message.split("\\", maxsplit=16)
                username = sys_msg[0]
                # logger_sub.info(f"{_time}: username; {username}\n sub_plan_name; {sub_plan_name}\nsub_msg; {sub_msg}\nsys_msg({len(sys_msg)}); {sys_msg}")
                total_sub_time = int(sys_msg[8].lstrip("s"))
                if len(sys_msg) > 10:
                    # total_sub_time = int(sys_msg[8].lstrip("s"))
                    streak_sub_time = int(sys_msg[13].lstrip("s"))
                else:
                    # total_sub_time = int(sys_msg[8].lstrip("s"))
                    streak_sub_time = 0
                logger_sim.info(f"{HYPE} {username} for the {subbie_tier_check(sub.sub_plan)} RESUB!!{f" {username} has been subbed for {total_sub_time:,} Months{f", currently on a {streak_sub_time} Streak!!" if streak_sub_time > 0 else "!!"}" if total_sub_time > 0 else ""}")
            except Exception as _error:
                logger.error(f"{fortime()}: ERROR 'on_sub/resub' - {_error}")
                return
    except Exception as _error:
        logger.error(f"{fortime()}: ERROR 'on_sub' - {_error}")
        return


async def on_user_join(event: JoinEvent) -> None:
    try:
        chatter_name = event.user_name
        streamer_name = bot.target_room[0]
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
        clear()
        save_data_stream(data_stream, SAVE_FILE)
        try:
            try:
                stream_stats = {
                    "bits": f"{data_stream['data']['bits']:,}",
                    "chat_msg_count": f"{data_stream['data']['chat_msg_count']:,}",
                    "chat_new_viewer": f"{data_stream['data']['chatters_new']:,}",
                    "subbies_gifted": f"{data_stream['data']['subbies']['gifted']:,}",
                    "subbies_new": f"{data_stream['data']['subbies']['new']:,}",
                    "subbies_resub": f"{data_stream['data']['subbies']['resub']:,}",
                    "subbies_total": f"{total_subbies():,}",
                    "raids-viewers": f"{data_stream['data']['raids']['total']:,}/{data_stream['data']['raids']['viewers']:,}",
                    "viewers": f"{viewers_fetch_current():,}",
                    "viewers_max": f"{data_stream['data']['viewers']['max']:,}",
                    "viewers_min": f"{data_stream['data']['viewers']['min']:,}",
                }
                print_stream_stats(stream_stats)
            except Exception as _error:
                logger.error(f"{fortime()}: ERROR 'on_stream_stats' - {_error}")
                pass
            user_input = input(f"{bot.long_dashes()}\n"
                               f"Enter 1 To View Names of Users\n"
                               f"Enter 0 To Exit\n"
                               f"Enter Nothing To Refresh\n")
            if user_input == "":
                pass
            elif user_input.isdigit():
                user_input = int(user_input)
                if user_input == 0:
                    break
                elif user_input == 1:
                    clear()
                    for username in sorted(users_in_chat[bot.target_room[0]]):
                        print(username)
                    print(f"{bot.long_dashes()}\nTotal; {viewers_fetch_current():,}")
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
        except SystemExit:
            break
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
    def shutdown(save_file_init: bool):
        if save_file_init:
            save_data_stream(data_stream, SAVE_FILE)
            logger.info(f"{fortime()}: '{SAVE_FILE}' saved!")
        shutdown_logger(log_list)
        clear()
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
        shutdown(SAVE_FILE_INIT)

    try:
        auth_dict = check_db_auth()
        if auth_dict is not None:
            bot = BotSetup(auth_dict['bot_id'], auth_dict['secret_id'])
            asyncio.run(auth_bot())
            user = asyncio.run(get_auth_user_id())
            data_stream, data_stream_timestamp = fetch_data_stream(data_stream_timestamp)
            SAVE_FILE = f"{init_time if data_stream_timestamp == 0 else datetime.strftime(datetime.fromtimestamp(data_stream_timestamp), FORMAT_TIME)}.json"
            SAVE_FILE_INIT = True
            if data_stream['info']['streamer'] is None:
                data_stream['info']['streamer'] = bot.target_room[0]
            if data_stream['info']['time']['started'] is None:
                data_stream['info']['time']['started'] = init_time
            asyncio.run(run())
        shutdown(SAVE_FILE_INIT)
    except KeyboardInterrupt:
        shutdown(SAVE_FILE_INIT)
    except Exception as e:
        logger.error(f"{fortime()}: Error in main loop -- {e}")
