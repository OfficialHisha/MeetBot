import database
import logging
from discord import Client
from os import environ
from asyncio import sleep
from dateparser import parse
from datetime import datetime, timedelta
from math import ceil
from re import compile, sub, search


class MeetBot(Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mention_re = compile(" *<@&?[0-9]*>")
        self._title_re = compile(" *[\"\'].*[\"\']")

        logging.basicConfig(filename='meetbot.log', level=int(environ["LOG_LEVEL"]))

        # Remove old meetings when we start the bot
        self.loop.run_until_complete(database.remove_old_meetings())

        # create the background tasks and run them in the background
        self.loop.create_task(self.check_meetings(10))

    @staticmethod
    async def get_labels_for_user(user):
        labels = [user.name]
        for role in user.roles:
            if role.name == "@everyone":
                continue
            labels.append(role.name)
        return labels

    @staticmethod
    async def is_number(number):
        try:
            int(number)
            return True
        except ValueError:
            return False

    @staticmethod
    async def cmd_help(channel):
        help_string = str('Commands:\n```\nmeeting setup [recurring] ["title"] <timestamp> <@attendees>' +
                          ' - Sets up a meeting for <@attendees> at the given <timestamp>\n' +
                          'meeting cancel <id> - Cancels the meeting with the given <id>\n' +
                          'meetings - Shows a list of meetings you are assigned to\n' +
                          'help - Shows this message\n```')

        await channel.send(help_string)

    async def check_meetings(self, wait_time=300):
        await self.wait_until_ready()
        await sleep(1)

        while not self.is_closed():
            await database.remove_old_meetings()
            for meeting in await database.get_upcoming_meetings(60):
                await self.check_upcoming_meeting(meeting)

            await sleep(wait_time)

    async def setup_meeting(self, channel, message, mentions, author, recurring=False):
        labels = dict()
        label_string = ""

        try:
            title = search(self._title_re, message).group()[1:].replace('"', '')
        except AttributeError:
            logging.debug("No meeting description was given, setting default name")
            title = 'meeting'

        # make datetime object
        parsed_datetime = parse(sub(self._title_re, '', message)[1:])
        if not parsed_datetime:
            logging.warning(f"Could not parse datetime object from {sub(self._title_re, '', message)[1:]}")
            await channel.send("There was an error while parsing the request, " +
                               "this can be caused by an error in the date format " +
                               "or wrong parameters given. " +
                               "Example: meeting setup @user1 @user2 october 3 at 7:30pm")
            return

        parsed_datetime = parsed_datetime.split('+')
        date_time = parsed_datetime[0]
        time_zone = 0
        if len(parsed_datetime) == 2:
            time_zone = parsed_datetime[1]

        # make the user list
        for label in mentions:
            labels[label.name] = label.id
            label_string += f"{label.name}:{label.id};"

        # remove the ';' after the last user
        label_string = label_string[:len(label_string) - 1]

        logging.info(f"{author} setup a meeting at {parsed_datetime}")
        logging.debug(f"Users: {label_string}. Time: {parsed_datetime}. Title: {title}. Recurring: {recurring}")
        await channel.send(f"{author} setup a meeting at {parsed_datetime}")

        await database.add_meeting(title, date_time, time_zone, label_string)

    async def cmd_meeting(self, message, mentions, author, channel):
        if message.startswith("setup"):
            if len(mentions) == 0:
                logging.info(f"{author} attempted to setup meeting for noone")
                await channel.send(f"""Not enough information to create meeting.
                                       Please define roles or users for the meeting
                                       by mentioning them in the command.""")
                return
            message = message[5:]
            if "recurring" in message:
                # setup a recurring meeting
                await self.setup_meeting(channel, sub(self._mention_re, '', message.replace(' recurring', '')),
                                         mentions, author, True)
            else:
                # setup meeting
                await self.setup_meeting(channel, sub(self._mention_re, '', message), mentions, author)

        elif message.startswith("cancel"):
            message = message[7:]
            # cancel meeting
            if not await self.is_number(message):
                logging.warning(f"Invalid ID '{message}' given for command 'meeting cancel'")
                await channel.send("Invalid ID. Syntax: meeting cancel <ID>")
                return

            if await database.remove_meeting(int(message)) == 0:
                await channel.send(f"There is no meeting with id {message}")
            else:
                await channel.send(f"Canceled meeting with id {message}")

    async def cmd_meetings(self, author, channel):
        labels = await self.get_labels_for_user(author)
        meetings = list()
        for label in labels:
            for meeting in await database.get_meetings_by_user(label):
                meetings.append(meeting)

        if len(meetings) == 0:
            meetings_string = "You have no upcoming meetings"
        else:
            meetings_string = "Your upcoming meetings are:\n```\n"
            for meeting in meetings:
                meetings_string += f"{meeting.id}: {meeting.date_time} - {meeting.description}\n"
            meetings_string += "```"

        await channel.send(meetings_string)

    async def check_upcoming_meeting(self, meeting):
        minutes_remaining = int(ceil((meeting.date_time - datetime.now()).seconds / 60))

        # if we have not notified the meeting, check what type of notification to give
        if meeting.notified == database.Notification.NONE:
            if meeting.date_time <= (datetime.now() + timedelta(minutes=10)):
                await self.notify_meeting(meeting, database.Notification.MINUTE, minutes_remaining)
            elif meeting.date_time <= (datetime.now() + timedelta(minutes=60)):
                await self.notify_meeting(meeting, database.Notification.HOUR, minutes_remaining)

        # if we have given the HOUR notification and there is ten minutes or less remaining
        # give the MINUTE notification
        elif (meeting.notified == database.Notification.HOUR and
              meeting.date_time <= (datetime.now() + timedelta(minutes=10))):
            await self.notify_meeting(meeting, database.Notification.MINUTE, minutes_remaining)

    async def notify_meeting(self, meeting, notification, minutes_remaining):
        await database.set_meeting_notification(meeting.id, notification)
        mentions = await self.mention_labels(meeting.user_list)
        await self.announce(f"Meeting '{meeting.description}' for {mentions} starts in {minutes_remaining} minutes")
        if notification == database.Notification.MINUTE:
            self.loop.create_task(self.set_timer(meeting, minutes_remaining))

    async def set_timer(self, meeting, alarm):
        await sleep(60 * alarm)
        mentions = await self.mention_labels(meeting.user_list)
        await self.announce(f"Meeting '{meeting.description}' for {mentions} starts now")
        await database.remove_meeting(meeting.id)

    async def get_labels(self, label_list):
        labels = label_list.split(';')
        mentionables = list()

        for label in labels:
            label_info = label.split(':')
            user = self.get_user(int(label_info[1]))
            if user:
                mentionables.append(user)
            else:
                mentionables.append(self.guilds[0].get_role(user))
        return mentionables

    async def mention_labels(self, labels):
        # if we get labels as a string we need to convert them to mentionable labels
        if type(labels) is str:
            labels = await self.get_labels(labels)

        mentions = ""
        for label in labels:
            mentions += f"{label.mention} "
        return mentions[:len(mentions) - 1]

    async def announce(self, message, channel_id=environ["MEETBOT_ANNOUNCE_CHANNEL"]):
        logging.debug(f"ANNOUNCEMENT - {message}")
        for guild in self.guilds:
            channel = guild.get_channel(channel_id)
            if channel:
                await channel.send(message)
                return

        logging.error(f"Channel with id '{channel_id}' not found in guilds")

    async def on_message(self, message):
        # if a command channel is set, don't take commands from other channels
        if (int(environ["MEETBOT_COMMAND_CHANNEL"]) != -1 and
                message.channel.id != int(environ["MEETBOT_COMMAND_CHANNEL"])):
            return

        # don't take commands from ourselves
        if message.author == self.user:
            return

        content = message.content.lower()
        author = message.author
        channel = message.channel
        # guild = message.author.guild

        try:
            if content.startswith("meetings"):
                logging.info(f"COMMAND - {author}: {message.content}")
                await self.cmd_meetings(author, channel)
            elif content.startswith("meeting"):
                logging.info(f"COMMAND - {author}: {message.content}")
                await self.cmd_meeting(content[8:], message.mentions + message.role_mentions, author, channel)
            elif content.startswith("help"):
                logging.info(f"COMMAND - {author}: {message.content}")
                await self.cmd_help(channel)
            elif content.startswith("channel"):
                logging.info(f"COMMAND - {author}: {message.content}")
                await channel.send(channel.id)
            else:  # unrecognised command given
                return
        except Exception as e:
            logging.exception(e)
            await channel.send("An unexpected error occurred")

    async def on_ready(self):
        logging.info(f'Logged in as: {self.user.name}')

        for meeting in await database.get_upcoming_meetings(10):
            minutes_remaining = int((meeting.date_time - datetime.now()).seconds / 60)
            if meeting.notified != database.Notification.MINUTE:
                await self.notify_meeting(meeting, database.Notification.MINUTE, minutes_remaining)
            else:
                self.loop.create_task(self.set_timer(meeting, minutes_remaining))


if __name__ == "__main__":
    bot = MeetBot()
    bot.run(environ["MEETBOT_TOKEN"])
