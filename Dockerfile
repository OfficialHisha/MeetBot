FROM python:3
COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt
COPY ./src/ /MeetBot
WORKDIR /MeetBot
CMD ["python", "bot.py"]
