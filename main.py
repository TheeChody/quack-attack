import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from colorama import Fore  # , Style
from twitchAPI.twitch import Twitch, TwitchUser
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.object.eventsub import ChannelBitsUseEvent, ChannelSubscribeEvent, ChannelSubscriptionGiftEvent, ChannelRaidEvent, ChannelChatNotificationEvent
from twitchAPI.eventsub.websocket import EventSubWebsocket
from twitchAPI.oauth import UserAuthenticationStorageHelper
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatCommand

if getattr(sys, 'frozen', False):
    folder_name = "DuckStuff"
    if sys.platform == "win32":
        from ctypes import windll, create_unicode_buffer
        buf = create_unicode_buffer(260)
        if windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
            data_path = f"{Path(buf.value)}\\{folder_name}\\"
        else:
            data_path = f"{Path(os.environ['USERPROFILE']) / 'Documents'}\\{folder_name}\\"
    else:
        data_path = f"{Path.home() / 'Documents'}\\{folder_name}\\"
else:
    data_path = f"{os.path.dirname(__file__)}\\"

directories = {
    "auth": f"{data_path}auth\\",
    "data": f"{data_path}data\\",
    "logs": f"{data_path}logs\\",
    "logs_archive": f"{data_path}logs\\archived\\"
}

Path(directories['auth']).mkdir(parents=True, exist_ok=True)
Path(directories['data']).mkdir(parents=True, exist_ok=True)
Path(directories['logs']).mkdir(parents=True, exist_ok=True)
Path(directories['logs_archive']).mkdir(parents=True, exist_ok=True)

nl = "\n"
log_list = []
raven_id = "114385193"
# raven_id = "268136120"  # mine
auth_json = f"{directories['auth']}auth_info.json"
twitch_token = f"{directories['auth']}twitch_token.json"
long_dashes = "-------------------------------------------------------------------"


# ----------------- Class Setup ----------------- #
class BotSetup(Twitch):
    def __init__(self, app_id: str, app_secret: str):
        super().__init__(app_id, app_secret)
        self.bot = Twitch
        self.target_rooms = [
            "theravenarmed"
            # "theechody"
        ]
        self.target_scopes = [
            AuthScope.BITS_READ,
            AuthScope.CHANNEL_BOT,
            AuthScope.CHANNEL_READ_SUBSCRIPTIONS,
            AuthScope.CHAT_READ,
            AuthScope.CHAT_EDIT,
            AuthScope.USER_BOT,
            AuthScope.USER_READ_CHAT,
            AuthScope.USER_WRITE_CHAT
        ]


# ----------------- BOT FUNCTIONS ----------------- #
async def auth_bot():
    twitch_helper = UserAuthenticationStorageHelper(bot, bot.target_scopes, Path(twitch_token))
    await twitch_helper.bind()
    logger.info(f"{fortime()}: Bot Authenticated Successfully!\n{long_dashes}")


def check_db_auth() -> dict | None:
    def fetch_stock_auth() -> dict | None:
        return {
            "bot_id": None,
            "secret_id": None,
            "db_string": None
        }

    if not os.path.exists(auth_json):
        save_json(fetch_stock_auth(), auth_json, True)
    _auth_dict = read_file(auth_json, {"json": True})
    if None in (_auth_dict['bot_id'], _auth_dict['secret_id']):
        _auth_dict = update_auth_json(_auth_dict)
    return _auth_dict


def cls():
    os.system('cls' if os.name == 'nt' else 'clear')


def colour(_colour: str, str_: str) -> str:
    if _colour == "blue":
        _colour = Fore.BLUE
    elif _colour == "cyan":
        _colour = Fore.CYAN
    elif _colour == "green":
        _colour = Fore.GREEN
    elif _colour == "purple":
        _colour = Fore.MAGENTA
    elif _colour == "red":
        _colour = Fore.RED
    elif _colour == "yellow":
        _colour = Fore.YELLOW
    else:
        _colour = Fore.RESET
    return f"{_colour}{str_}{Fore.RESET}"


def fortime() -> str:
    return datetime.now().strftime('%y-%m-%d %H:%M:%S')


async def get_auth_user_id() -> TwitchUser | None:
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


def read_file(file_name: str, return_type: type(bool) | type(dict) | type(float) | type(int) | type(list) | type(str)) -> bool | dict | float | int | list | str | None:
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


def save_json(data: dict, file_save: str, first_create: bool = False):
    if data is None:
        logger.error(f"{fortime()}: Data is None!!!")
        return
    with open(file_save, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)
    if first_create:
        logger.info(f"{fortime()}: First Time Run Detected!!\n'{auth_json}' File Created!")
        time.sleep(5)


def shutdown_logger(_log_list: list):
    logging.shutdown()
    for entry in _log_list:
        try:
            os.rename(f"{directories['logs']}{entry}", f"{directories['logs_archive']}{entry}")
            print(f"{entry} moved to archives..")
        except Exception as _error:
            print(_error)
            time.sleep(10)
            pass


def setup_logger(name: str, log_file: str, _log_list: list, level=logging.INFO):
    try:
        local_logger = logging.getLogger(name)
        handler = logging.FileHandler(f"{directories['logs']}{log_file}", mode="w", encoding="utf-8")
        if name == "logger":
            console_handler = logging.StreamHandler()
            local_logger.addHandler(console_handler)
        local_logger.setLevel(level)
        local_logger.addHandler(handler)
        _log_list.append(f"{log_file}")
        return local_logger
    except Exception as _error:
        print(f"{fortime()}: ERROR in setup_logger - {name}/{log_file}/{level} -- {_error}")
        time.sleep(15)
        _log_list.append(None)
        return None


def subbie_tier_check(raw_tier: str):
    if raw_tier == "1000":
        return "Tier 1"
    elif raw_tier == "2000":
        return "Tier 2"
    else:
        return "Tier 3"


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
    save_json(current_dict, auth_json)
    return current_dict


# ----------------- MAIN_BOT_FUNCTIONS ----------------- #
async def on_stream_bitties(data: ChannelBitsUseEvent):
    try:
        logger_sim.info(f"{fortime()}: on_stream_bitties: !hyp {data.event.user_name} cheering with {data.event.bits} bitties!!")
    except Exception as e:
        logger.error(f"{fortime()}: Error in 'on_stream_bitties' -- {e}")
        return


async def on_message(msg: ChatMessage):
    logger_chat.info(f"{fortime()}: on_message: {msg.user.id}|{msg.user.display_name}; {msg.text}")


async def on_ready(event: EventData):
    for username in bot.target_rooms:
        await event.chat.join_room(username)
        logger.info(f"{fortime()}: Joined {username} chat!")
        await asyncio.sleep(1.5)
        cls()


async def on_stream_subbie(data: ChannelSubscribeEvent):
    try:
        if not data.event.is_gift:
            logger_sim.info(f"{fortime()}: on_stream_subbie: !hyp {data.event.user_name} with a {subbie_tier_check(data.event.tier)} subscription")
    except Exception as e:
        logger.error(f"{fortime()}: Error in 'on_stream_subbie' | {e}\n{data.event}")


async def on_stream_subbie_gift(data: ChannelSubscriptionGiftEvent):
    try:
        logger_sim.info(f"{fortime()}: on_stream_subbie_gift; !hyp {data.event.user_name} for the {data.event.total} gifted subbie{'s' if data.event.total < 1 else ''}!! A new total of {data.event.cumulative_total}")
    except Exception as e:
        logger.error(f"{fortime()}: Error in 'on_stream_subbie_gift' | {e}\n{data.event}")


async def on_stream_raid_in(data: ChannelRaidEvent):
    try:
        logger_sim.info(f"{fortime()}: on_stream_raid_in: Welcome in {data.event.from_broadcaster_user_name}'s {data.event.viewers} Raiders!!!")
    except Exception as e:
        logger.error(f"{fortime()}: Error in 'on_stream_raid_in' | {e}\n{data.event}")


async def on_stream_raid_out(data: ChannelRaidEvent):
    try:
        logger_sim.info(f"{fortime()}: on_stream_raid_out: {data.event.from_broadcaster_user_name} has raided out with {data.event.viewers} to https://twitch.tv/{data.event.to_broadcaster_user_name}")
    except Exception as e:
        logger.error(f"{fortime()}: Error in 'on_stream_raid_out' | {e}\n{data.event}")


async def on_stream_chat_notification(data: ChannelChatNotificationEvent):
    try:
        logger_test.info(f"{fortime()}: on_stream_chat_notification: {data.event}")
    except Exception as e:
        logger.error(f"{fortime()}: Error in 'on_stream_chat_notification' | {e}\n{data.event}")


# async def test_command(cmd: ChatCommand):
#     await cmd.reply(f"{cmd.user.display_name} I am responding to you!")
#     if cmd.parameter == "param":
#         await cmd.reply("Paramater detected")


# ----------------- MAIN_BOT_LOOP ----------------- #
async def run():
    async def shutdown():
        chat.stop()
        await asyncio.sleep(1)
        await event_sub.stop()
        await asyncio.sleep(1)
        await bot.close()
        await asyncio.sleep(1)

    chat = await Chat(bot)
    chat.register_event(ChatEvent.READY, on_ready)
    chat.register_event(ChatEvent.MESSAGE, on_message)
    # chat.register_command("test", test_command)
    chat.start()

    event_sub = EventSubWebsocket(bot)
    event_sub.start()
    await event_sub.listen_channel_bits_use(raven_id, on_stream_bitties)
    await event_sub.listen_channel_chat_notification(raven_id, user.id, on_stream_chat_notification)
    await event_sub.listen_channel_raid(on_stream_raid_in, to_broadcaster_user_id=raven_id)
    await event_sub.listen_channel_raid(on_stream_raid_out, from_broadcaster_user_id=raven_id)
    await event_sub.listen_channel_subscribe(raven_id, on_stream_subbie)
    await event_sub.listen_channel_subscription_gift(raven_id, on_stream_subbie_gift)

    await asyncio.sleep(.25)
    while True:
        try:
            user_input = input("Enter 0 To Exit\n")
            if user_input.isdigit():
                user_input = int(user_input)
                if user_input == 0:
                    break
        except Exception as e:
            logger.error(f"{fortime()}: Error in main loop -- {e}")
            try:
                continue
            except Exception as ee:
                logger.error(f"{fortime()}: Error continuing from last error -- {ee}")
                await asyncio.sleep(2)
                break
    await shutdown()


if __name__ == "__main__":
    init_time = fortime().replace(' ', '--').replace(':', '-')
    logger = setup_logger("logger", f"main_log--{init_time}.log", log_list)
    logger_chat = setup_logger("logger_chat", f"chat_log--{init_time}.log", log_list)
    logger_test = setup_logger("logger_test", f"test_log--{init_time}.log", log_list)
    logger_sim = setup_logger("logger_sim", f"sim_log--{init_time}.log", log_list)
    auth_dict = check_db_auth()
    if auth_dict is not None:
        bot = BotSetup(auth_dict['bot_id'], auth_dict['secret_id'])
        asyncio.run(auth_bot())
        user = asyncio.run(get_auth_user_id())
        if user is not None:
            asyncio.run(run())

    shutdown_logger(log_list)
