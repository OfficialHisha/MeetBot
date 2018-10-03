import secrets
from peewee import MySQLDatabase, Model, DateTimeField, TextField
from datetime import timedelta, datetime
import asyncio

_database = MySQLDatabase(secrets.database_db, user=secrets.database_user,
                          password=secrets.database_pass, host=secrets.database_host,
                          port=secrets.database_port)

class BaseModel(Model):
    class Meta:
        database = _database

class Meeting(BaseModel):
    date_time = DateTimeField()
    user_list = TextField()

def initialize_database():
    _database.create_tables([Meeting])

def add_meeting(time, users):
    Meeting.create(date_time=time, user_list=users)

def remove_old_meetings():
    Meeting.delete().where(Meeting.date_time < datetime.now()).execute()

def get_meeting_by_id(id):
    return Meeting.select().where(Meeting.id == id)

def get_upcoming_meetings(time=10):
    return Meeting.select().where(Meeting.date_time <= (datetime.now() + timedelta(minutes=time)))