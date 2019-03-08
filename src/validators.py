from os import environ
from re import compile
from dateparser import parse

_mention_re = compile(" *<@&?[0-9]*>")


async def mention_validator(mention_string):
    mentions = mention_string.split(' ')

    for mention in mentions:
        if not _mention_re.fullmatch(mention):
            return False
    return True


async def time_validator(time_string):
    if not parse(time_string):
        return False
    return True


async def number_validator(number):
    try:
        int(number)
        return True
    except ValueError:
        return False


async def channel_validator(channel):
    if int(environ["MEETBOT_COMMAND_CHANNEL"]) != -1:
        return channel.id == int(environ["MEETBOT_COMMAND_CHANNEL"])
    return True
