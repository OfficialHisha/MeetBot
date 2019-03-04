#MeetBot

####Required permissions:
* Role permissions:
    * Manage Channels
    * Mention Everyone

* Channel category permissions:
    * Read Text Channels And See Voice Channels

* Command channel permissions:
    * Read Messages
    * Send Messages

* Announcement channel permissions:
    * Send Messages
    
---
####Environment Variables
* LOG_LEVEL
    * CRITICAL: 50
    * ERROR: 40
    * WARNING: 30
    * INFO: 20
    * DEBUG: 10
    * NOTSET: 0
* MEETBOT_TOKEN
    * Your bot token
* MEETBOT_DATABASE
    * Database name
* MEETBOT_DATABASE_USERNAME
    * Database user name
* MEETBOT_DATABASE_PASSWORD
    * Database user password
* MEETBOT_DATABASE_HOST
    * Database ip or hostname
* MEETBOT_DATABASE_PORT
    * Database port
* MEETBOT_COMMAND_CHANNEL
    * Channel in which MeetBot will look for commands (-1 for any channel the bot has read permissions for)
* MEETBOT_ANNOUNCE_CHANNEL
    * Channel in which MeetBot will make announcements