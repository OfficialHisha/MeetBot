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
    description = TextField()
    date_time = DateTimeField()
    user_list = TextField()
    notified = SmallIntegerField(default=Notification.NONE)

    class Meta:
        database = _database


Meeting.create_table(True)
_database.allow_sync = False


async def add_meeting(description, time, users):
    await _objects.create(Meeting, description=description, date_time=time, user_list=users)


async def remove_meeting(meeting_id):
    meeting = await _objects.get(Meeting, id=meeting_id)
    await _objects.delete(meeting)


async def remove_old_meetings():
    old_meetings = await _objects.execute(Meeting.select().where(
        Meeting.date_time < datetime.utcnow()))
    for meeting in old_meetings:
        await _objects.delete(meeting)


async def set_meeting_notification(meeting_id, notification):
    meeting = await _objects.get(Meeting, id=meeting_id)
    meeting.notified = notification
    await _objects.update(meeting)


async def get_meeting_by_id(meeting_id):
    return await _objects.get(Meeting, id=meeting_id)


async def get_meetings_by_mentions(mentions):
    return await _objects.execute(Meeting.select().where(any(Meeting.user_list.contains(mention) for mention in mentions)))


async def get_upcoming_meetings(time=10):
    return await _objects.execute(Meeting.select().where(
        Meeting.date_time <= (datetime.utcnow() + timedelta(minutes=time))))
