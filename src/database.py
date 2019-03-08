from os import environ
from peewee import Model, DateTimeField, TextField, SmallIntegerField
from peewee_async import MySQLDatabase, Manager
from datetime import timedelta, datetime
from enum import IntEnum

_database = MySQLDatabase(database=environ["MEETBOT_DATABASE"],
                          user=environ["MEETBOT_DATABASE_USERNAME"],
                          password=environ["MEETBOT_DATABASE_PASSWORD"],
                          host=environ["MEETBOT_DATABASE_HOST"],
                          port=int(environ['MEETBOT_DATABASE_PORT']))
_objects = Manager(_database)


class Notification(IntEnum):
    NONE = 0
    HOUR = 1
    MINUTE = 2


class Meeting(Model):
    guild = TextField()
    description = TextField()
    date_time = DateTimeField()
    user_list = TextField()
    notified = SmallIntegerField(default=Notification.NONE)
    channel = TextField(default="-1")

    class Meta:
        database = _database


Meeting.create_table(True)
_database.allow_sync = False


async def add_meeting(guild, description, time, users):
    await _objects.create(Meeting, guild=guild, description=description, date_time=time, user_list=users)


async def remove_meeting(meeting_id):
    meeting = await _objects.get(Meeting, id=meeting_id)
    await _objects.delete(meeting)


async def set_meeting_description(meeting_id, new_description):
    meeting = await _objects.get(Meeting, id=meeting_id)
    meeting.description = new_description
    await _objects.update(meeting)


async def set_meeting_time(meeting_id, new_time):
    meeting = await _objects.get(Meeting, id=meeting_id)
    meeting.date_time = new_time
    meeting.notified = Notification.NONE
    await _objects.update(meeting)


async def set_meeting_participants(meeting_id, new_participants):
    meeting = await _objects.get(Meeting, id=meeting_id)
    meeting.user_list = new_participants
    await _objects.update(meeting)


async def set_meeting_channel(meeting_id, channel):
    meeting = await _objects.get(Meeting, id=meeting_id)
    meeting.channel = channel
    await _objects.update(meeting)


async def set_meeting_notification(meeting_id, notification):
    meeting = await _objects.get(Meeting, id=meeting_id)
    meeting.notified = notification
    await _objects.update(meeting)


async def get_meeting_by_id(meeting_id):
    return await _objects.get(Meeting, id=meeting_id)


async def get_meetings_by_mentions(mentions):
    meetings = list()
    for mention in mentions:
        meetings += await _objects.execute(Meeting.select().where(Meeting.user_list.contains(mention)))
    return meetings


async def get_upcoming_meetings(time=10):
    return await _objects.execute(Meeting.select().where(
        Meeting.date_time <= (datetime.utcnow() + timedelta(minutes=time))))


async def get_elapsed_meetings():
    return await _objects.execute(Meeting.select().where(Meeting.date_time < datetime.utcnow() - timedelta(hours=12)))
