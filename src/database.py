import secrets
from peewee import MySQLDatabase, Model, DateTimeField, TextField, SmallIntegerField
from datetime import timedelta, datetime
from enum import IntEnum


class Notification(IntEnum):
    NONE = 0
    HOUR = 1
    MINUTE = 2


_database = MySQLDatabase(secrets.database_db, user=secrets.database_user,
                          password=secrets.database_pass, host=secrets.database_host,
                          port=secrets.database_port)


class BaseModel(Model):
    class Meta:
        database = _database


class Meeting(BaseModel):
    description = TextField()
    date_time = DateTimeField()
    user_list = TextField()
    notified = SmallIntegerField(default=Notification.NONE)


def initialize_database():
    _database.create_tables([Meeting])


def add_meeting(description, time, users):
    return Meeting.create(description=description, date_time=time, user_list=users)


def remove_meeting(id):
    return Meeting.delete().where(Meeting.id == id).execute()


def remove_old_meetings():
    return Meeting.delete().where(Meeting.date_time < datetime.now()).execute()


def set_meeting_notification(id, notification):
    return Meeting.update({Meeting.notified: notification}).where(Meeting.id == id).execute()


def get_meeting_by_id(id):
    return Meeting.select().where(Meeting.id == id)


def get_meetings_by_label(name):
    return Meeting.select().where(Meeting.user_list.contains(name))


def get_upcoming_meetings(time=10):
    return Meeting.select().where(Meeting.date_time <= (datetime.now() + timedelta(minutes=time)))
