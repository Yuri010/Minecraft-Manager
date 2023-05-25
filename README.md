# Minecraft-Manager
Simple Discord bot and some scripts to manage a self-hosted Minecraft server

## Part 1: Bot Setup
 1. Go to the Discord Developer Portal and create a new application
 2. Go to your application, go to the bot tab and create your bot
 3. Copy the bot token somewhere, you will need this later so keep hold of it but **DON'T SHARE IT WITH ANYONE**
 4. Add the bot to the server you want:
    1. Copy the client ID and replace it in the following link:\
       https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=397284599872&scope=bot
    2. Follow that link and add it to the server you want.
 5. Customize the bot further, however you want (Changing the name and pfp in the "Bot" tab for example)

## Part 2: Server Setup
 1. Install a recent Java JDK (18 or higher is recommended)\
    https://www.oracle.com/java/technologies/downloads/#jdk20-windows
 2. Install Python (3.11)\
    https://www.python.org/downloads/
 3. Install the following Python modules: `requests`, `mcrcon` and `discord.py`
    1. Open Command Prompt
    2. Enter the following command: ``pip install requests mcrcon discord.py`` and hit enter
    3. Wait for them to install
 4. Download a Minecraft Server JAR
    - Official: https://www.minecraft.net/en-us/download/server
    - Spigot (supports plugins): https://getbukkit.org/download/spigot
 5. Create a new directory somewhere (I recommend your Documents folder) and move the JAR file in there.
 6. Double click the JAR file and wait a few seconds, some files should start appearing, of which also a "EULA.txt"
    Open this file and replace ``EULA=false`` with ``EULA=true`` if you agree to the Minecraft Server EULA
 7. Create an account at Ngrok and download the Windows executable (https://ngrok.com/download) \
    Then move the Ngrok executable to the server folder.

## Part 3: Configuration
 1. Authenticate Ngrok (Once you create an account you should see instructions right on the dashboard)
    1. Open Command Prompt and navigate to the server directory (e.g. ``cd %userprofile%\Documents\Server``) will navigate to C:\Users\<Username>\Documents\Server
    2. Type ``ngrok config add-authtoken YOUR_TOKEN``, replace ``YOUR_TOKEN`` with the token displayed on the Ngrok Dashboard
 2. Open Config.cfg in any text editor of your choice
 3. Under the header ``[PythonConfig]`` replace-
    - The ``token`` value with your bot token
    - The ``bot_owner_id`` value with your Discord User ID
    - The ``rcon_password`` value with a (strong) password of your choice.
 4. Under the header ``[BatchConfig]`` replace-
    - The example text ``spigot-1.19.4`` with the name of your server JAR file
    - The ``maxram`` value with the maximum amount of RAM you want the server to be able to use
    - The ``minram`` value with the minimum amount of RAM the server should (be able to) use
 5. Save and close the Config.cfg and now open the ``server.properties`` file in the server folder and change the following values:
    - ``enable-rcon=false`` to ``enable-rcon=true``
    - ``rcon.password=`` to ``rcon.password=YourBeautifulPasswordYouEnteredEarlier`` (for example ``rcon_password=#ILovePonies123``)
 6. Save and close the server.properties file.

Your ``config.cfg`` should now look a little like this:
```ini
[PythonConfig]
TOKEN = ABCdEXF1HIJ2LmN3Pqr4TUvwXy.A56D78.HIJkl9NOPQrSTUV0XYzABcdEFgHiJkLMNOPWRs
required_role = Minecrafter
bot_owner_id = 123456789087654321
rcon_host = 127.0.0.1
rcon_port = 25575
rcon_password = #ILovePonies123

[BatchConfig]
jar = server.jar
port = 25565
maxram = 4096M
minram = 1024M
```

## Part 4: Running it all
After having followed the full setup, everything should be installed and configured correctly.
Just a brief checklist:
- [ ] Discord Application and Bot set-up and added to server
- [ ] Java and Python installed, including the python modules
- [ ] Downloaded a Server.jar and Ngrok.exe and dumped them in a handy folder
- [ ] Started the Server.jar once and accepted the UELA
- [ ] Created an account for and authenticated Ngrok
- [ ] Made a handy subfolder in that handy folder and dumped the scripts in there
- [ ] Edited the config.cfg with your values
- [ ] Edited the server.properties to accept Console Connections by the bot

If you have all that, all you have to do is just run the bot.bat, it should start right up and say it is "Bot is ready, logged in as <Bot_Username>".
Then just simply type ``$start`` in the #bot-commands channel of your server which you added the bot to and it should start right up.

## Troubleshooting (If needed)
Even if you followed all the steps shown above, some errors might still pop up.
Which is why I made this section of the readme.

If you were to run into any errors, please report them by creating a new issue in this repository.
When creating an issue, clearly explain which script you had problems with and what you might have already tried to fix it.

Some error messages are pretty straightforward, like from ``start.bat``: "Java could not be found" or from ``Updater.bat``: "The configuration file isn't set up" 
While some might need some more digging, for example when you try to start the bot and it just crashes or when the updater simply overwrites all the scripts with error messages.\
For these specific cases I have made a startup command for the bot.bat and updater.bat scripts:
``<script>.bat -debug``. When executing this is, it should try and start the script and show any error messages. Please include these error messages with your issue. (if present)
