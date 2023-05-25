# Minecraft-Manager
Simple Discord bot and some scripts to manage a self-hosted Minecraft server

### Pre- Basic Setup
 1. Go to the Discord Developer Portal and create a new application
 2. Go to your application, go to the bot tab and create your bot
 3. Copy the bot token, you will need this later so keep hold of it but **DON'T SHARE IT WITH ANYONE**
 4. Add the bot to the server you want (some additional steps are required for doing so, but I'm not gonna write all that down here)

### Basic Setup
*very limited, requires common sense and some steps not mentioned*
 1.1 Install Python (3.11)
 1.2 Install the following Python modules: `requests`, `mcrcon` and `discord.py`
 2. Create a new (sub)directory in the directory containing the server and move the files in there
 3. Download the Ngrok executable into that directory and authenticate it (see the Ngrok dashboard)
 4. Configure Config.cfg
 5. Run ``bot.bat`` and simply type ``#start`` in the Discord server with the bot and the server should start
