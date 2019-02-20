FROM python:3-slim
RUN apt update
RUN apt install -y gcc git
RUN git clone https://github.com/OfficialHisha/MeetBot.git
WORKDIR /MeetBot
RUN pip install -r requirements.txt
CMD ["python", "./src/bot.py"]
