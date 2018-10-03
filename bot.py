import secrets
import discord
import asyncio
import database
import datetime

class MeetBot(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # create the background task and run it in the background
        self.bg_task = self.loop.create_task(self.check_meetings(3))

    async def check_meetings(self, wait_time=300):
        await self.wait_until_ready()
        await asyncio.sleep(1)
        while not self.is_closed():
            print("Checking meetings")

            database.remove_old_meetings()
            for meeting in database.get_upcoming_meetings(60):
                print("Meeting upcoming: " + str(meeting.date_time))

            await asyncio.sleep(wait_time)
            

    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        content = message.content.lower()
        channel = message.channel
        guild = message.author.guild

        await channel.send('Recieved')

        if content.startswith('test'):
            database.add_meeting(datetime.datetime.now() + datetime.timedelta(minutes=10), message.author)

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

client = MeetBot()
client.run(secrets.bot_token)