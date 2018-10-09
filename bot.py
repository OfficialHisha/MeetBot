from math import ceil
import secrets
import discord
import asyncio
import database
import datetime
import dateparser
import time
import re

class MeetBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mention_re = re.compile(" *<@[0-9]*>")
        self._title_re = re.compile(" *[\"\'].*[\"\']")

        database.remove_old_meetings()

        # create the background task and run it in the background
        self.loop.create_task(self.check_meetings(10))

    async def is_number(self, input):
        try:
            int(input)
            return True
        except ValueError:
            return False

    async def setup_meeting(self, channel, message, mentions, author, recurring=False):
        users = dict()
        user_string = ""
        print(message)
        try:
            title = re.search(self._title_re, message).group()[1:].replace('"', '')
        except AttributeError:
            title = 'meeting'

        # make datetime object
        datetime = dateparser.parse(re.sub(self._title_re, '', message)[1:])
        if datetime == None:
            await channel.send("There was an error while parsing the request, " +
                               "this can be caused by an error in the date format " + 
                               "or wrong parameters given. " + 
                               "Example: meeting setup @user1 @user2 october 3 at 7:30pm")
            return

        # make the user list
        for user in mentions:
            users[user] = user.id
            user_string += f"{user}:{user.id};"
        # remove the ';' after the last user
        user_string = user_string[:len(user_string) - 1]
        


        print(f"Users: {user_string}. Time: {datetime}. Title: {title}. Recurring: {recurring}")
        await channel.send(f"{author} setup a meeting at {datetime}")

        database.add_meeting(title, datetime, user_string)

    async def cmd_meeting(self, message, mentions, author, channel):
        if message.startswith("setup"):
            message = message[5:]
            if "recurring" in message:
                # setup a recurring meeting
                await self.setup_meeting(channel, re.sub(self._mention_re, '', message.replace(' recurring', '')), mentions, author, True)
            else:
                # setup meeting
                await self.setup_meeting(channel, re.sub(self._mention_re, '', message), mentions, author)

        elif message.startswith("cancel"):
            message = message[7:]
            # cancel meeting
            if not await self.is_number(message):
                await channel.send("Invalid ID. Syntax: meeting cancel <ID>")
                return
            
            if database.remove_meeting(int(message)) == 0:
                await channel.send(f"There is no meeting with id {message}")
            else:
                await channel.send(f"Canceled meeting with id {message}")
            
    async def cmd_meetings(self, author, channel):
        meetings = database.get_meetings_by_name(str(author))
        meetings_string = "Your upcoming meetings are:\n```\n"
        for meeting in meetings:
            meetings_string += f"{meeting.id}: {meeting.date_time} - {meeting.description}\n"
        meetings_string += "```"

        await channel.send(meetings_string)

    async def cmd_help(self, channel):
        help_string = str('Commands:\n```\nmeeting setup [recurring] ["title"] <timestamp> <@attendees>' +
                          ' - Sets up a meeting for <@attendees> at the given <timestamp>\n' +
                          'meeting cancel <id> - Cancels the meeting with the given <id>\n' + 
                          'meetings - Shows a list of meetings you are assigned to\n' +
                          'help - Shows this message\n```')

        await channel.send(help_string)

    async def check_meetings(self, wait_time=300):
        await self.wait_until_ready()
        await asyncio.sleep(1)
        
        while not self.is_closed():
            for meeting in database.get_upcoming_meetings(60):
                await self.check_upcoming_meeting(meeting)
            database.remove_old_meetings()
            await asyncio.sleep(wait_time)
            
    async def check_upcoming_meeting(self, meeting):
        if(meeting.notified == database.Notification.NONE):
            minutes_remaining = int(ceil((meeting.date_time - datetime.datetime.now()).seconds / 60))

            if(meeting.date_time < (datetime.datetime.now() + datetime.timedelta(minutes=10))):
                await self.notify_meeting(meeting, database.Notification.MINUTE, minutes_remaining)
            elif(meeting.date_time < (datetime.datetime.now() + datetime.timedelta(minutes=60))):
                await self.notify_meeting(meeting, database.Notification.HOUR, minutes_remaining)
            
        elif(meeting.notified == database.Notification.HOUR and
             meeting.date_time < (datetime.datetime.now() + datetime.timedelta(minutes=10))):
                await self.notify_meeting(meeting, database.Notification.MINUTE, minutes_remaining)
            

    async def notify_meeting(self, meeting, notification, minutes_remaining):
        database.set_meeting_notification(meeting.id, notification)
        mentions = await self.mention_users(meeting.user_list)
        await self.announce(f"Meeting '{meeting.description}' for {mentions} starts in {minutes_remaining} minutes")
        if(notification == database.Notification.MINUTE):
            self.loop.create_task(self.set_timer(meeting, minutes_remaining))

    async def set_timer(self, meeting, alarm):
        await asyncio.sleep(60 * alarm)
        mentions = await self.mention_users(meeting.user_list)
        await self.announce(f"Meeting '{meeting.description}' for {mentions} starts now")
        database.remove_meeting(meeting.id)

    async def get_users(self, user_list):
        users = user_list.split(';')
        actual_users = list()

        for user in users:
            user_info = user.split(':')
            actual_users.append(self.get_user(int(user_info[1])))
        return actual_users

    async def mention_users(self, users):
        # if we get users as a string we need to convert them to actual users
        if type(users) is str:
            users = await self.get_users(users)

        mentions = ""
        for user in users:
            mentions += f"{user.mention} "
        return mentions[:len(mentions) - 1]

    async def announce(self, message, channel=secrets.bot_announcement_channel_id):
        print(message)
        await self.guilds[0].get_channel(channel).send(message)# this might cause problems if the bot
                                                               # is in multiple servers, will have to
                                                               # check up on that

    async def on_message(self, message):
        # if a command channel is set, don't take commands from other channels
        if (secrets.bot_cmd_channel_id != -1 and
           message.channel.id != secrets.bot_cmd_channel_id):
            return

        # don't take commands from ourselves
        if message.author == self.user:
            return

        print(message.content)

        content = message.content.lower()
        author = message.author
        channel = message.channel
        guild = message.author.guild

        try:
            if content.startswith("meetings"):
                await self.cmd_meetings(author, channel)
            elif content.startswith("meeting"):
                await self.cmd_meeting(content[8:], message.mentions, author, channel)
            elif content.startswith("help"):
                await self.cmd_help(channel)
            else:# unrecognised command given
                return
        except Exception as e:
            print(e)
            await channel.send("An unexpected error occurred")

        if content.startswith('channel'):
            cmd = content.split(' ')
            
            if len(cmd) != 3:
                await channel.send("Incorrect use of command 'channel'")
                return

            if cmd[1] == "create":
                await guild.create_voice_channel(cmd[2], category=guild.get_channel(channel.category_id), reason="Created by " + str(message.author))
                await channel.send(f"Created channel '{cmd[2]}'")
                return
            elif cmd[1] == "delete":
                for guild_channel in client.get_all_channels():
                    if str(guild.get_channel(guild_channel.category_id)) == "Developer corner":
                        if str(guild_channel) == cmd[2]:
                            await guild_channel.delete()
                            await channel.send(f"Deleted channel '{cmd[2]}'")
                            return
                
                await channel.send(f"Channel '{cmd[2]}' not found")
                return
            else:
                await channel.send("Incorrect use of command 'channel'")
                return

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

        for meeting in database.get_upcoming_meetings(10):
            minutes_remaining = int((meeting.date_time - datetime.datetime.now()).seconds / 60)
            if(meeting.notified != database.Notification.MINUTE):
                await self.notify_meeting(meeting, database.Notification.MINUTE, minutes_remaining)
            else:
                self.loop.create_task(self.set_timer(meeting, minutes_remaining))

database.initialize_database()
client = MeetBot()
client.run(secrets.bot_token)