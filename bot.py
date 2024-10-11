"""
bot.py

Version: 1.3.0

This module contains the main logic for the Minecraft Discord bot. It sets
up the bot, defines command handlers for various bot functionalities,
and manages interactions with the Minecraft server. The bot supports commands
such as starting/stopping the server, managing snapshots, and verifying users.

Usage:
    - Run this module to start the bot and listen for commands in Discord.
    - The bot uses the command prefix `$` to interact with users.

Key Commands:
    - `start`: Starts the Minecraft server.
    - `stop`: Stops the Minecraft server.
    - `snapshots`: Manage world snapshots (list, create, delete, restore, download).
    - `verify`: Links a Discord account to a Minecraft account.
    - `ping`: Measures the bot's latency.

Database:
    - The bot uses an SQLite database to manage user verification and snapshot
      information.

Configuration:
    - The bot's configuration is loaded from a `config.cfg` file, which should
      contain the necessary settings (e.g., bot token, RCON credentials).

Notes:
    - Ensure that the Minecraft server is running before executing commands
      that interact with it.
    - The bot requires specific roles and permissions to execute certain commands.
"""


# Standard Library Imports
import asyncio
import logging
import configparser
import socket
import sqlite3
import subprocess
import time

# Third-party imports
import aiohttp
import discord
import mcrcon
from discord.ext import commands

# First-party imports
import bot_modules


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

BOT_VERSION = "1.3.0"

conn = sqlite3.connect('minecraft_manager.db')
c = conn.cursor()

config = configparser.ConfigParser()
config.read('config.cfg')

TOKEN = config.get('PythonConfig', 'TOKEN')
REQUIRED_ROLE = config.get('PythonConfig', 'required_role')
BOT_OWNER_ID = int(config.get('PythonConfig', 'bot_owner_id'))
PORT = config.get("PythonConfig", "port")
RCON_HOST = config.get('PythonConfig', 'rcon_host')
RCON_PORT = int(config.get('PythonConfig', 'rcon_port'))
RCON_PASSWORD = config.get('PythonConfig', 'rcon_password')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

bot.server_running = False


@bot.command(name='start')
async def start(ctx):
    discord_id = ctx.author.id

    if ctx.author.id == BOT_OWNER_ID:
        pass
    elif bot_modules.has_required_role(ctx):
        pass
    else:
        is_op, error_message = bot_modules.has_operator(discord_id)
        if not is_op:
            embed = discord.Embed(
                title=':x: Missing Permissions',
                description=f'{error_message}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

    bot.server_running = await bot_modules.start_server(ctx, bot)


@bot.command(name='stop')
async def stop_command(ctx):
    discord_id = ctx.author.id

    if ctx.author.id == BOT_OWNER_ID:
        pass
    else:
        # Check if the user is a Minecraft operator
        is_op, error_message = bot_modules.has_operator(discord_id)
        if not is_op:
            embed = discord.Embed(
                title=':x: Missing Permissions',
                description=f':x: {error_message}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

    if not bot.server_running:
        embed = discord.Embed(
            title=':x: Server Offline!',
            description='The Minecraft server is not running.',
            color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    try:
        with mcrcon.MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as rcon:
            rcon.command('stop')
            embed = discord.Embed(
                title=":hourglass: Server Stopping...",
                description='Sent the `stop` command to the Minecraft server.',
                color=discord.Color.blue())
            stop = await ctx.send(embed=embed)

    except mcrcon.MCRconException:
        embed = discord.Embed(
            title=':x: Server Error!',
            description='Failed to send the `stop` command to the Minecraft server.',
            color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Checking if server actually went offline
    for attempt in range(5):
        logging.debug("Checking server state... Attempt %d/5", attempt + 1)
        bot.server_running = bot_modules.check_server_running(host='localhost', port=PORT)

        if not bot.server_running:
            logging.info("Server stopped successfully")
            embed = discord.Embed(
                title=":stop_button: Server Stopped",
                description='Server stopped successfully',
                color=discord.Color.green())
            await stop.edit(embed=embed)

            try:
                # Terminate Ngrok process
                result = subprocess.call('taskkill /im ngrok.exe /f', shell=True)
                if result == 0:
                    logging.info("Ngrok terminated successfully.")
                else:
                    logging.error("Failed to terminate Ngrok process. Error code: %d", result)
            except Exception as e:
                logging.error("Error terminating Ngrok process: %s", e)
            break

        await asyncio.sleep(2)

    if bot.server_running:
        logging.error("Failed to stop the Minecraft server")
        embed = discord.Embed(
            title=':x: Server Error!',
            description='Server failed to stop',
            color=discord.Color.red())
        await stop.edit(embed=embed)


@bot.command(name='shutdown')
async def shutdown_bot(ctx):
    if ctx.author.id == BOT_OWNER_ID:
        embed = discord.Embed(
            title=':stop_button: Bot Shutting Down',
            description='Shutting down the bot...',
            color=discord.Color.blue())
        await ctx.send(embed=embed)
        await bot.close()
    else:
        embed = discord.Embed(
            title="x: Missing Permissions",
            description="Only the Minecraft Server Owner can issue this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@bot.command(name='update')
async def update_bot(ctx):
    if ctx.author.id == BOT_OWNER_ID:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    "https://api.github.com/repos/yuri010/minecraft-manager/releases/latest") as response:
                data = await response.json()
                latest_version = data.get("tag_name", "Unknown")

        if latest_version < BOT_VERSION:
            embed = discord.Embed(
                title=':x: You are in the future!',
                description=f'Current version ({BOT_VERSION})\
                              is newer than the latest public build ({latest_version})!\n\
                              Update aborted.',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        if latest_version > BOT_VERSION:
            embed = discord.Embed(
                title=':arrows_counterclockwise: Update Available!',
                description=f'A new version ({latest_version} over {BOT_VERSION}) is available!\n\
                              Do you want to update now?',
                color=discord.Color.blue()
            )
            message = await ctx.send(embed=embed)
            await message.add_reaction('✅')
            await message.add_reaction('❌')

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ['✅', '❌'] and reaction.message.id == message.id

            try:
                reaction, _ = await bot.wait_for('reaction_add', timeout=60.0, check=check)

                if str(reaction.emoji) == '✅':
                    embed = discord.Embed(
                        title=':arrows_counterclockwise: Bot Restarting...',
                        description='The bot will restart to perform an update. Please wait...',
                        color=discord.Color.blue()
                    )
                    await message.edit(embed=embed)
                    await message.clear_reactions()

                    try:
                        # Start the updater process
                        command = 'start cmd /c "updater.bat -autostart"'
                        subprocess.Popen(command, shell=True)
                        await bot.close()
                    except Exception as e:
                        embed = discord.Embed(
                            title=':x: Update Error!',
                            description=f'An error occurred while starting the update: {str(e)}',
                            color=discord.Color.red()
                        )
                        await message.edit(embed=embed)

                else:
                    embed = discord.Embed(
                        description=':x: Update canceled.',
                        color=discord.Color.red()
                    )
                    await message.edit(embed=embed)

            except asyncio.TimeoutError:
                embed = discord.Embed(
                    description=':x: Update process timed out.',
                    color=discord.Color.red()
                )
                await message.edit(embed=embed)

        else:
            embed = discord.Embed(
                title=':white_check_mark: Up-to-date!',
                description=f'The bot is already up to date (Version {BOT_VERSION}).',
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)

    else:
        embed = discord.Embed(
            title="❌ Missing Permissions",
            description="Only the Minecraft Server Owner can issue this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@bot.command(name='console')
async def console_command(ctx, *, command):
    discord_id = ctx.author.id

    # Permissions check
    if ctx.author.id != BOT_OWNER_ID and not bot_modules.has_required_role(ctx):
        # Check if the user is a Minecraft operator
        is_op, error_message = bot_modules.has_operator(discord_id)
        if not is_op:
            embed = discord.Embed(
                title=':x: Missing Permissions',
                description=f'{error_message}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

    # Check if the server is running
    if not bot.server_running:
        embed = discord.Embed(
            title=':x: Server Offline!',
            description='The Minecraft server is not running.',
            color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    try:
        # Set up an RCON connection with a timeout
        with mcrcon.MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT, timeout=5) as rcon:
            response = rcon.command(command)
            embed = discord.Embed(
                title='Minecraft Console',
                description=f'Command: {command}',
                color=discord.Color.green())
            embed.add_field(name='Output', value=response)
            await ctx.send(embed=embed)

    except mcrcon.MCRconException as e:
        # Handle RCON-specific errors
        embed = discord.Embed(
            title='Minecraft Console',
            description=f'Command: {command}',
            color=discord.Color.red())
        embed.add_field(name='Error', value=str(e))
        await ctx.send(embed=embed)

    except TimeoutError:
        # Handle timeout errors
        embed = discord.Embed(
            title='❌ Timed Out',
            description=':x: Failed to connect to the server within the timeout period.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@console_command.error
async def console_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ Missing Argument",
            description="Please provide a command to execute.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@bot.command(name='status')
async def status_command(ctx):
    embed_color = discord.Color.red()
    public_ip = await bot_modules.get_public_ip() if bot.server_running else None

    if bot.server_running:
        embed_color = discord.Color.green()
        try:
            # Check if public_ip is a string and is in the expected format
            if isinstance(public_ip, str):
                if ':' in public_ip:
                    host, port = public_ip.replace('tcp://', '').split(':')[:2]
                else:
                    host, port = public_ip, '25565'  # Use public_ip as host, default to port 25565
            else:
                # Handle the case where public_ip is None or not a string
                host, port = None, None
                logging.error("Failed to retrieve public IP at 'status' command.")

            # Only proceed if host and port are valid
            if host and port:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(3)
                    result = sock.connect_ex((host, int(port)))

                if result != 0:
                    embed_color = discord.Color.red()
        except TypeError:
            logging.error("Failed to check server status: string conversion error.")

    embed = discord.Embed(title='Server Status', color=embed_color)
    embed.add_field(name='Status', value='Running' if bot.server_running else 'Stopped', inline=False)

    # Update IP field based on validity
    if isinstance(public_ip, str):
        embed.add_field(name='IP', value=public_ip.replace('tcp://', ''), inline=False)
    else:
        embed.add_field(name='IP', value='N/A', inline=False)  # Public IP retrieval failed

    if bot.server_running and host and port:  # Only ping if valid host and port are available
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(3)
                start_time = time.time()
                result = sock.connect_ex((host, int(port)))
                end_time = time.time()

            if result == 0:
                ping_ms = round((end_time - start_time) * 1000, 2)
                embed.add_field(name='Ping', value=f'Latency: {ping_ms} ms', inline=False)
            else:
                embed.add_field(name='Ping', value='Failed to ping server: Port is closed', inline=False)
        except Exception as e:
            embed.add_field(name='Ping', value=f'Failed to ping server: {str(e)}', inline=False)

    await ctx.send(embed=embed)


@bot.command(name='snapshots')
async def snapshots_command(ctx, action=None, *args):
    discord_id = ctx.author.id

    if action == 'list' or action is None:  # When 'list' or no arguments are given, simply list the snapshots
        await bot_modules.list_snapshots(ctx)
        return

    if action == 'create':
        # Check if the user is the bot owner first
        if discord_id != BOT_OWNER_ID:
            # If not the owner, check if they are an operator
            is_op, error_message = bot_modules.has_operator(discord_id)
            if not is_op:
                embed = discord.Embed(
                    title=':x: Missing Permissions',
                    description=f'{error_message}',
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
        await bot_modules.create_snapshot(ctx, bot, *args)
        return

    # Check if user is owner before executing descructive commands
    if action in ['delete', 'restore'] and discord_id != BOT_OWNER_ID:
        embed = discord.Embed(
            title=':x: Missing Permissions',
            description='You do not have permission to use this command.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Ensure snapshot name is provided for 'delete', 'restore', and 'download'
    if action in ['delete', 'restore', 'download']:
        if not args:  # If no snapshot name is provided
            embed = discord.Embed(
                title=':x: Missing Arguments',
                description=f'You must provide a snapshot name for the `{action}` command.',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

    # Process the commands if snapshot name is provided
    if action == 'delete':
        await bot_modules.delete_snapshot(ctx, bot, ' '.join(args))
    elif action == 'restore':
        await bot_modules.restore_snapshot(ctx, bot, ' '.join(args))
    elif action == 'download':
        await bot_modules.download_snapshot(ctx, ' '.join(args))
    else:
        embed = discord.Embed(
            title=':x: Unknown Argument',
            description=f'Unknown action `{action}`.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@bot.command(name='info')
async def info_command(ctx, action=None):
    if action == 'snapshots':
        await bot_modules.info_snapshots(ctx, bot)
    else:
        await bot_modules.info(ctx, bot)


@bot.command(name='verify')
async def verify_command(ctx):
    await bot_modules.verify(ctx, bot)


@bot.command(name='ping')
async def ping_command(ctx):
    await bot_modules.ping(ctx)


@bot.event
async def on_ready():
    logging.info("Bot is ready. Logged in as %s", bot.user.name)
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,
                                                        name="over a Minecraft Server"))

if __name__ == "__main__":
    bot.run(TOKEN)
