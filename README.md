# Minecraft-Manager
Simple Discord bot and some scripts to manage a self-hosted Minecraft server

### Pre- Basic Setup
 1. Go to the Discord Developer Portal and create a new application
 2. Go to your application, go to the bot tab and create your bot
 3. Copy the bot token, you will need this later so keep hold of it but **DON'T SHARE IT WITH ANYONE**
 4. Add the bot to the server you want (some additional steps are required for doing so, but I'm not gonna write all that down here)

### Basic Setup
*very limited, requires common sense and some steps not mentioned*
 1. Install Python (3.11)
 2. Move the files into the directory containing the server(.jar)
 3. Download the Ngrok executable into that directory and authenticate it (see the Ngrok dashboard)
 4. Change some variables (like the owner ID and bot token in ``bot.py``)
 5. Run ``bot.bat`` and simply type ``#start`` in the Discord server with the bot and the server should start
