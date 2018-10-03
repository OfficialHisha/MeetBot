import secrets
import discord
import asyncio
import database
import datetime
import time

class MeetBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        database.remove_old_meetings()

        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.check_meetings(10))

    async def check_meetings(self, wait_time=300):
        await self.wait_until_ready()
        await asyncio.sleep(1)
        
        while not self.is_closed():
            print("Checking meetings")
            for meeting in database.get_upcoming_meetings(60):
                await self.check_upcoming_meeting(meeting)
            await asyncio.sleep(wait_time)
            
    async def check_upcoming_meeting(self, meeting):
        if(meeting.notified == database.Notification.NONE):
            minutes_remaining = int((meeting.date_time - datetime.datetime.now()).seconds / 60)

            if(meeting.date_time < (datetime.datetime.now() + datetime.timedelta(minutes=10))):
                await self.notify_meeting(meeting, database.Notification.MINUTE, minutes_remaining)
            elif(meeting.date_time < (datetime.datetime.now() + datetime.timedelta(minutes=60))):
                await self.notify_meeting(meeting, database.Notification.HOUR, minutes_remaining)
            
        elif(meeting.notified == database.Notification.HOUR and
             meeting.date_time < (datetime.datetime.now() + datetime.timedelta(minutes=10))):
                await self.notify_meeting(meeting, database.Notification.MINUTE, minutes_remaining)
            

    async def notify_meeting(self, meeting, notification, minutes_remaining):
        database.set_meeting_notification(meeting.id, notification)
        print("Notification for " + str(meeting.user_list) + " for meeting at "
                + str(meeting.date_time) + ". (" + str(minutes_remaining) + " minutes from now)")
        if(notification == database.Notification.MINUTE):
            await self.set_timer(meeting, minutes_remaining)

    async def set_timer(self, meeting, alarm):
        print("Timer started with time: " + str(alarm) + " minutes")
        start_time = time.time()
        end_time = start_time + 60 * alarm

        try:
            while(time.time() < end_time):
                await asyncio.sleep(1)
                print(str(int(end_time - time.time())) + " seconds remaining")
        except Exception as e:
            print(e)

        print("Meeting for " + str(meeting.user_list) + " starts now!")
        database.remove_meeting(meeting.id)


    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        content = message.content.lower()
        channel = message.channel
        guild = message.author.guild

        await channel.send('Recieved')

        if content.startswith('test'):
            time = datetime.datetime.now() + datetime.timedelta(minutes=10)
            print("Setup meeting for " + str(message.author) + " at " + str(time))
            database.add_meeting(time, message.author)

        if content.startswith('channel'):
            cmd = content.split(' ')
            
            if len(cmd) != 3:
                await channel.send("Incorrect use of command 'channel'")
                return

            if cmd[1] == "create":
                await guild.create_voice_channel(cmd[2], category=guild.get_channel(channel.category_id), reason="Created by " + str(message.author))
                await channel.send("Created channel '" + cmd[2] + "'")
                return
            elif cmd[1] == "delete":
                for guild_channel in client.get_all_channels():
                    if str(guild.get_channel(guild_channel.category_id)) == "Developer corner":
                        if str(guild_channel) == cmd[2]:
                            await guild_channel.delete()
                            await channel.send("Deleted channel '" + cmd[2] + "'")
                            return
                
                await channel.send("Channel '" + cmd[2] + "' not found")
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
                await self.set_timer(meeting, minutes_remaining)

client = MeetBot()
database.initialize_database()
client.run(secrets.bot_token)