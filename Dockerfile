FROM python:3
COPY . /MeetBot
WORKDIR /MeetBot
RUN pip install -r requirements.txt
CMD python bot.py
