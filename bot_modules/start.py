"""
start.py

Version 1.3.0

This modules houses all logic for starting the Minecraft server with the assigned configuration,
starting the Ngrok tunnel and sending the IP in chat.

Functions
    - fetch_ngrok_url(): (Internal) Fetches the public Ngrok tunnel IP to send in chat.
    - start_server(ctx, bot):
      Actually starts the server

Notes:
    - The module uses Discord's embed functionality to communicate with users in
      a visually appealing manner.
"""

# Standard library imports
import asyncio
import logging
import subprocess
import configparser
from pathlib import Path

# Third-party imports
import discord

# First-party imports
from bot_modules import utils


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

script_path = Path(__file__).resolve().parent
root_path = script_path.parent

config = configparser.ConfigParser()
config.read('config.cfg')

BOT_OWNER_ID = int(config.get('PythonConfig', 'bot_owner_id'))
JAR = root_path.parent / config.get("PythonConfig", "jar")
PORT = config.get("PythonConfig", "port")
MAXRAM = config.get("PythonConfig", "maxram")
MINRAM = config.get("PythonConfig", "minram")
NGROK_PATH = root_path.parent / 'ngrok.exe'


# Function to start the Minecraft server
async def start_server(ctx, bot):
    if bot.server_running:
        embed = discord.Embed(
            title=':x: Server Running',
            description='The Minecraft server is already running.',
            color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Validate configurations
    if not JAR.exists():  # Ensure you call exists() as a function
        logging.error("Jarfile not found at %s", JAR)
        embed = discord.Embed(
            title=':x: Fatal Error',
            description=f'Server JAR file could not be found, failed to start server.\n\
                         Tried looking in {JAR}',
            color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title=':rocket: Server Starting...',
        description='Starting the Minecraft server, please wait...',
        color=discord.Color.blue())
    message = await ctx.send(embed=embed)

    # Prepare the command to start the server
    COMMAND = f'java -Xmx{MAXRAM} -Xms{MINRAM} -DIReallyKnowWhatIAmDoingISwear -jar "{JAR}"'
    logging.info("Starting server with command: %s", COMMAND)

    # Start the server process
    subprocess.Popen(
        COMMAND,
        shell=True,
        stdout=subprocess.DEVNULL,  # Suppress standard logs
        stderr=subprocess.DEVNULL,   # Suppress error logs
        cwd=root_path.parent  # Make sure it uses the actual server directory rather than scripts
    )
    # Wait for the server to be ready
    await asyncio.sleep(10)

    # Check if the server is reachable
    for attempt in range(5):
        logging.debug("Checking server state... Attempt %d/5", attempt + 1)
        bot.server_running = utils.check_server_running(host='localhost', port=PORT)

        if bot.server_running:
            logging.info("Local server started successfully")
            break
        await asyncio.sleep(2)  # Wait before the next check

    # Notify users if the server is up
    if bot.server_running:
        NGROK_COMMAND = [str(NGROK_PATH), 'tcp', PORT]
        logging.info("Starting Ngrok with command: %s", NGROK_COMMAND)

        # Start ngrok
        subprocess.Popen(
            NGROK_COMMAND,
            shell=True,
            stdout=subprocess.DEVNULL,  # Suppress standard logs
            stderr=subprocess.DEVNULL,   # Suppress error logs
            cwd=root_path.parent
        )
        # Fetch the public URL from ngrok
        await asyncio.sleep(2)  # Wait a bit for Ngrok to actually come available
        public_ip = await utils.get_public_ip()
        if public_ip:
            logging.info("Server started successfully, available at: %s", public_ip)
            public_ip = public_ip.replace('tcp://', '')
            embed = discord.Embed(
                title=':white_check_mark: Server Started!',
                description=f"The Minecraft server has started successfully.\n\
                                The server is now accessible at: **{public_ip}**",
                color=discord.Color.green()
            )
            await message.edit(embed=embed)
            return bot.server_running

        logging.error("Failed to resolve public IP at 'get_public_ip'")
        embed = discord.Embed(
            title=':x: Server Error!',
            description='Failed to retrieve the public IP of the server.',
            color=discord.Color.red())
    else:
        logging.error("Failed to 'check_server_running'")
        embed = discord.Embed(
            title=':x: Server Error!',
            description='Failed to retrieve server status.',
            color=discord.Color.red())

    await message.edit(embed=embed)
