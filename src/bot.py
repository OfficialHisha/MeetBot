import validators
import database
import logging
from discord.ext import commands
from os import environ
from asyncio import sleep
from dateparser import parse
from datetime import datetime, timedelta
from math import ceil

logging.basicConfig(filename='meetbot.log', level=int(environ["LOG_LEVEL"]))
bot = commands.Bot(command_prefix='!')


async def announce(message, channel_id=int(environ["MEETBOT_ANNOUNCE_CHANNEL"])):
    logging.debug(f"ANNOUNCEMENT - {message}")
    channel = await find_channel_by_id(channel_id)
    await channel.send(message)


async def set_timer(meeting, alarm):
    await sleep(60 * alarm)
    await announce(f"{meeting.id}:{meeting.description} for {meeting.user_list} starts now")


async def notify_meeting(meeting, notification, minutes_remaining):
    meeting_notification = database.set_meeting_notification(meeting.id, notification)
    announcement = announce(f"{meeting.id}:{meeting.description} for {meeting.user_list} starts in {minutes_remaining} minutes")

    if notification == database.Notification.MINUTE:
        bot.loop.create_task(set_timer(meeting, minutes_remaining))

    await meeting_notification
    await announcement


async def find_channel_by_id(channel_id):
    for channel in bot.get_all_channels():
        if channel.id == int(channel_id):
            return channel

    logging.error(f"Channel with id '{channel_id}' not found in channels")
    print(f"Channel with id '{channel_id}' not found in channels")


async def find_guild_by_id(guild_id):
    for guild in bot.guilds:
        if guild.id == int(guild_id):
            return guild

    logging.error(f"Guild {guild_id} not found in guilds")
    print(f"Guild {guild_id} not found in guilds")


async def prepare_meeting(meeting):
    if not meeting.channel == -1:
        return  # The meeting has already been prepared

    guild = await find_guild_by_id(meeting.guild)
    channel = await guild.create_voice_channel(f"{meeting.id}: {meeting.description}")
    await database.set_meeting_channel(meeting.id, channel.id)
    await announce(f"I have assigned channel '{channel.name}' for {meeting.id}:{meeting.description}, it will be deleted in 12 hours")


async def check_upcoming_meeting(meeting):
    minutes_remaining = int(ceil((meeting.date_time - datetime.utcnow()).seconds / 60))

    # if we have not notified the meeting, check what type of notification to give
    if meeting.notified == database.Notification.NONE:
        if meeting.date_time <= (datetime.utcnow() + timedelta(minutes=10)):
            await notify_meeting(meeting, database.Notification.MINUTE, minutes_remaining)
            await prepare_meeting(meeting)

        elif meeting.date_time <= (datetime.utcnow() + timedelta(minutes=60)):
            await notify_meeting(meeting, database.Notification.HOUR, minutes_remaining)

    # if we have given the HOUR notification and there is ten minutes or less remaining
    # give the MINUTE notification and prepare the meeting channel
    elif (meeting.notified == database.Notification.HOUR and
          meeting.date_time <= (datetime.utcnow() + timedelta(minutes=10))):
        await notify_meeting(meeting, database.Notification.MINUTE, minutes_remaining)
        await prepare_meeting(meeting)


async def cleanup_meeting(meeting):
    channel = await find_channel_by_id(meeting.channel)
    await channel.delete()
    await database.remove_meeting(meeting.id)
    logging.info(f"Meeting {meeting.id} was cleaned up")
    print(f"Meeting {meeting.id} was cleaned up")


async def check_meetings(wait_time=300):
    await bot.wait_until_ready()
    await sleep(1)

    while not bot.is_closed():
        for meeting in await database.get_elapsed_meetings():
            await cleanup_meeting(meeting)
        for meeting in await database.get_upcoming_meetings(60):
            await check_upcoming_meeting(meeting)

        await sleep(wait_time)
bot.loop.create_task(check_meetings(10))


@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    print(f'Logged in as {bot.user.name}')
    print('------')


@bot.event
async def on_command_error(ctx, exception):
    logging.error(exception)
    print(exception)
    await ctx.send("An unexpected error occurred")


@bot.command(name="id")
@commands.has_role("Admin")
async def channel_id_cmd(ctx):
    await ctx.channel.send(f"Channel ID: {ctx.channel.id}")


@bot.command(name="meetings")
async def meetings_cmd(ctx, time_zone="UTC"):
    if not await validators.channel_validator(ctx.channel):
        return

    mentions = [ctx.author.mention]
    for role in ctx.author.roles:
        mentions.append(role.mention)

    meetings = await database.get_meetings_by_mentions(mentions)

    if len(meetings) == 0:
        meetings_string = "You have no upcoming meetings"
    else:
        meetings_string = "Your upcoming meetings are:\n```\n"
        for meeting in meetings:
            meeting_dt = parse(str(meeting.date_time),
                               settings={'TIMEZONE': "UTC", 'TO_TIMEZONE': time_zone, 'RETURN_AS_TIMEZONE_AWARE': False})
            meetings_string += f"{meeting.id}: {meeting_dt} {time_zone} - {meeting.description}\n"
        meetings_string += "```"

    await ctx.send(meetings_string)


@bot.group(name="meeting")
async def meeting_cmd(ctx):
    if not await validators.channel_validator(ctx.channel):
        return


@meeting_cmd.command(name="create")
async def meeting_create_cmd(ctx, description, participants, time):
    if not await validators.channel_validator(ctx.channel):
        return

    if not await validators.mention_validator(participants):
        logging.info(f"{ctx.author} failed mention validation check for 'meeting create' command\n"
                     f"Input was: {ctx.message}")
        print(f"{ctx.author} failed mention validation check for 'meeting create' command\n"
              f"Input was: {ctx.message}")
        await ctx.send("There seem to be a problem with your parameters\n"
                       "Use !help to see proper use of my functionality")
        return

    if not await validators.time_validator(time):
        logging.info(f"{ctx.author} failed time validation check for 'meeting create' command\n"
                     f"Input was: {ctx.message}")
        print(f"{ctx.author} failed time validation check for 'meeting create' command\n"
              f"Input was: {ctx.message}")
        await ctx.send("There seem to be a problem with your parameters\n"
                       "Use !help to see proper use of my functionality")
        return

    iso_time = parse(time, settings={'TO_TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': False}).isoformat()
    db_call = database.add_meeting(ctx.guild.id, description, iso_time, participants)

    logging.info(f"{ctx.author} set up a meeting at {iso_time} for {participants}")
    logging.debug(f"Meeting:\nGuild id: {ctx.guild.id}\n Description: {description}\n Time: {iso_time}\n Participants: {participants}")
    print(f"{ctx.author} set up a meeting at {iso_time} for {participants}")
    print(f"Meeting:\n Guild id: {ctx.guild.id}\n Description: {description}\n Time: {iso_time}\n Participants: {participants}")

    await ctx.send("I have set up your meeting")
    await db_call


@meeting_cmd.command(name="cancel")
async def meeting_cancel_cmd(ctx, meeting_id):
    if not await validators.channel_validator(ctx.channel):
        return

    if not await validators.number_validator(meeting_id):
        await ctx.send("Please supply an id for the meeting you wish to cancel\n"
                       "Use !help to see proper use of my functionality")
        logging.info(f"{ctx.author} failed number validation check for 'meeting cancel' command\n"
                     f"Input was: {ctx.message}")
        print(f"{ctx.author} failed number validation check for 'meeting cancel' command\n"
              f"Input was: {ctx.message}")
        return

    meeting = await database.get_meeting_by_id(meeting_id)
    db_call = cleanup_meeting(meeting)
    await ctx.send(f"Canceled meeting with id {meeting_id}")
    await db_call


@meeting_cmd.group(name="edit")
async def meeting_edit_cmd(ctx):
    if not await validators.channel_validator(ctx.channel):
        return


@meeting_edit_cmd.command(name="name")
async def meeting_edit_name_cmd(ctx, meeting_id, new_name):
    db_call = database.set_meeting_description(meeting_id, new_name)
    await ctx.send(f"Changed the name of meeting {meeting_id}")
    await db_call


@meeting_edit_cmd.command(name="time")
async def meeting_edit_time_cmd(ctx, meeting_id, new_time):
    if not await validators.time_validator(new_time):
        logging.info(f"{ctx.author} failed time validation check for 'meeting create' command\n"
                     f"Input was: {ctx.message}")
        print(f"{ctx.author} failed time validation check for 'meeting create' command\n"
              f"Input was: {ctx.message}")
        await ctx.send("There seem to be a problem with your parameters\n"
                       "Use !help to see proper use of my functionality")
        return

    iso_time = parse(new_time, settings={'TO_TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': False}).isoformat()
    db_call = database.set_meeting_time(meeting_id, iso_time)
    await ctx.send(f"Changed the time of meeting {meeting_id}")
    await db_call


@meeting_edit_cmd.command(name="members")
async def meeting_edit_members_cmd(ctx, meeting_id, new_members):
    if not await validators.mention_validator(new_members):
        logging.info(f"{ctx.author} failed mention validation check for 'meeting create' command\n"
                     f"Input was: {ctx.message}")
        print(f"{ctx.author} failed mention validation check for 'meeting create' command\n"
              f"Input was: {ctx.message}")
        await ctx.send("There seem to be a problem with your parameters\n"
                       "Use !help to see proper use of my functionality")
        return

    db_call = database.set_meeting_participants(meeting_id, new_members)
    await ctx.send(f"Changed participants of meeting {meeting_id}")
    await db_call

if __name__ == "__main__":
    bot.run(environ["MEETBOT_TOKEN"])
