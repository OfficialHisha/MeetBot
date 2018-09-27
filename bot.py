import secrets
import discord
import asyncio

class MeetBot(discord.Client):
    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def on_message(self, message):
        # don't respond to ourselves
        if message.author == self.user:
            return

        content = message.content.lower()
        channel = message.channel
        guild = message.author.guild

        print()
        await channel.send('Recieved')

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
                channels = list()

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

client = MeetBot()
client.run(secrets.bot_token)