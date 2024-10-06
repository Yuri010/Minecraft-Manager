# version 1.3.0
import discord
from discord.ext import commands
import bot_modules
import subprocess
import time
import mcrcon
import configparser
import socket
import asyncio
import sqlite3
import json
import os
import aiohttp

BOT_VERSION = "1.3.0"

conn = sqlite3.connect('minecraft_manager.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS verification (
                discord_id INTEGER PRIMARY KEY,
                minecraft_name TEXT
            )''')

config = configparser.ConfigParser()
config.read('config.cfg')

TOKEN = config.get('PythonConfig', 'TOKEN')
required_role = config.get('PythonConfig', 'required_role')
bot_owner_id = int(config.get('PythonConfig', 'bot_owner_id'))
rcon_host = config.get('PythonConfig', 'rcon_host')
rcon_port = int(config.get('PythonConfig', 'rcon_port'))
rcon_password = config.get('PythonConfig', 'rcon_password')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

server_running = False


def has_required_role(ctx):
    role = discord.utils.get(ctx.guild.roles, name=required_role)
    return role in ctx.author.roles


def has_operator(discord_id):
    try:
        # Check the database if the user has verified their Minecraft account
        c.execute("SELECT * FROM verification WHERE discord_id=?", (discord_id,))
        result = c.fetchone()

        if result is None:
            # User hasn't verified their Minecraft account
            print(f"Error at 'has_operator': User {discord_id} not verified.")
            return False, 'You need to verify your Minecraft account first using the `$verify` command.'

        minecraft_username = result[1]

        # Check if ops.json exists and is valid
        with open('../ops.json', 'r') as file:
            if os.stat('../ops.json').st_size == 0:
                print("Error at 'has_operator': ops.json is empty.")
                return False, 'Operator list is empty. Please contact an admin.'

            ops_data = json.load(file)

        # Check if the Minecraft username is an operator
        for op in ops_data:
            if op['name'] == minecraft_username:
                return True, None  # User is an operator, no error message needed

        # If user is verified but not an operator
        return False, 'You do not have operator permissions on the Minecraft server.'

    except (FileNotFoundError, json.JSONDecodeError):
        print("Error at 'has_operator': Failed loading ops.json.")
        return False, 'Failed to load operator list. Please contact an admin.'


@bot.command(name='start')
async def start(ctx):
    discord_id = ctx.author.id

    if ctx.author.id == bot_owner_id:
        pass
    elif has_required_role(ctx):
        pass
    else:
        # Check if the user is a Minecraft operator
        is_op, error_message = has_operator(discord_id)
        if not is_op:
            embed = discord.Embed(
                description=f':x: {error_message}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

    global server_running

    if server_running:
        embed = discord.Embed(description=':x: The Minecraft server is already running.', color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(description=':rocket: Starting the Minecraft server, please wait...',
                          color=discord.Color.blue())
    message = await ctx.send(embed=embed)

    try:
        subprocess.Popen('start cmd /c "start.bat -y"', shell=True)
        server_running = True
        await bot.change_presence(activity=discord.Game(name="a Minecraft Server"))

        await asyncio.sleep(45)
        public_ip = await bot_modules.get_public_ip()
        if public_ip:
            public_ip = public_ip.replace('tcp://', '')
            embed = discord.Embed(
                title=':white_check_mark: The Minecraft server has started successfully.',
                description=f"The server is now accessible at: **{public_ip}**",
                color=discord.Color.green()
            )
            await message.edit(embed=embed)
        else:
            embed = discord.Embed(description=':x: Failed to retrieve the public IP of the server.',
                                  color=discord.Color.red())
            await message.edit(embed=embed)

    except Exception as e:
        embed = discord.Embed(description=f':x: An error occurred while starting the server: {str(e)}',
                              color=discord.Color.red())
        await message.edit(embed=embed)


@bot.command(name='stop')
async def stop_command(ctx):
    discord_id = ctx.author.id

    if ctx.author.id == bot_owner_id:
        pass
    else:
        # Check if the user is a Minecraft operator
        is_op, error_message = has_operator(discord_id)
        if not is_op:
            embed = discord.Embed(
                description=f':x: {error_message}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

    if not server_running:
        embed = discord.Embed(description=':x: The Minecraft server is not running.', color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    try:
        with mcrcon.MCRcon(rcon_host, rcon_password, port=rcon_port) as rcon:
            rcon.command('stop')
            embed = discord.Embed(description=':stop_button: Sent the `stop` command to the Minecraft server.',
                                  color=discord.Color.green())
            await ctx.send(embed=embed)
    except mcrcon.MCRconException:
        embed = discord.Embed(description=':x: Failed to send the `stop` command to the Minecraft server.',
                              color=discord.Color.red())
        await ctx.send(embed=embed)


@bot.command(name='shutdown')
async def shutdown_bot(ctx):
    if ctx.author.id == bot_owner_id:
        embed = discord.Embed(description=':stop_button: Shutting down the bot...', color=discord.Color.red())
        await ctx.send(embed=embed)
        await bot.close()
    else:
        embed = discord.Embed(
            title="❌ Missing Permissions",
            description="Only the Minecraft Server Owner can issue this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@bot.command(name='update')
async def update_bot(ctx):
    if ctx.author.id == bot_owner_id:

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.github.com/repos/yuri010/minecraft-manager/releases/latest"
            ) as response:
                data = await response.json()
                latest_version = data.get("tag_name", "Unknown")

        if latest_version < BOT_VERSION:
            embed = discord.Embed(
                description=f'❌ Current version ({BOT_VERSION}) is newer than\
                    the latest public build ({latest_version})!\n\
                        Update aborted.',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        if latest_version > BOT_VERSION:
            embed = discord.Embed(
                description=f'🔄 A new version ({latest_version} over {BOT_VERSION}) is available!\
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
                    confirm_embed = discord.Embed(
                        description='🔄 The bot will restart to perform an update. Please wait...',
                        color=discord.Color.blue()
                    )
                    await message.edit(embed=confirm_embed)
                    await message.clear_reactions()
                    try:
                        subprocess.Popen('start cmd /c "updater.bat -autostart"', shell=True)
                        await bot.close()
                    except Exception as e:
                        error_embed = discord.Embed(
                            description=f':x: An error occurred while starting the update: {str(e)}',
                            color=discord.Color.red()
                        )
                        await message.edit(embed=error_embed)
                else:
                    cancel_embed = discord.Embed(
                        description=':x: Update canceled.',
                        color=discord.Color.green()
                    )
                    await message.edit(embed=cancel_embed)

            except asyncio.TimeoutError:
                timeout_embed = discord.Embed(
                    description=':x: Update process timed out.',
                    color=discord.Color.red()
                )
                await message.edit(embed=timeout_embed)

        else:
            up_to_date_embed = discord.Embed(
                description=f'✅ The bot is already up to date (Version {BOT_VERSION}).',
                color=discord.Color.green()
            )
            await ctx.send(embed=up_to_date_embed)

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

    if ctx.author.id == bot_owner_id:
        pass
    elif has_required_role(ctx.author):
        pass
    else:
        # Check if the user is a Minecraft operator
        is_op, error_message = has_operator(discord_id)
        if not is_op:
            embed = discord.Embed(
                description=f':x: {error_message}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

    try:
        with mcrcon.MCRcon(rcon_host, rcon_password, port=rcon_port) as rcon:
            response = rcon.command(command)
            embed = discord.Embed(title='Minecraft Console', description=f'Command: {command}',
                                  color=discord.Color.green())
            embed.add_field(name='Output', value=response)
            await ctx.send(embed=embed)
    except mcrcon.MCRconException as e:
        embed = discord.Embed(title='Minecraft Console', description=f'Command: {command}', color=discord.Color.red())
        embed.add_field(name='Error', value=str(e))
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
    public_ip = await bot_modules.get_public_ip() if server_running else None

    if server_running:
        embed_color = discord.Color.green()
        try:
            host, port = public_ip.replace('tcp://', '').split(':')[:2] if ':' in public_ip else (public_ip, '25565')

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(3)
                result = sock.connect_ex((host, int(port)))

            if result != 0:
                embed_color = discord.Color.red()
        except TypeError:
            print('Failed to check server status: string conversion error.')

    embed = discord.Embed(title='Server Status', color=embed_color)
    embed.add_field(name='Status', value='Running' if server_running else 'Stopped', inline=False)
    embed.add_field(name='IP', value=public_ip.replace('tcp://', '') if server_running else 'N/A', inline=False)

    if server_running:
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
        if discord_id != bot_owner_id:
            # If not the owner, check if they are an operator
            is_op, error_message = has_operator(discord_id)
            if not is_op:
                embed = discord.Embed(
                    description=f':x: {error_message}',
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
                return
        await bot_modules.create_snapshot(ctx, bot, server_running, suppress_success_message=False)
        return

    # Check if user is owner before executing descructive commands
    if action in ['delete', 'restore'] and discord_id != bot_owner_id:
        embed = discord.Embed(
            description=':x: You do not have permission to use this command.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Ensure snapshot name is provided for 'delete', 'restore', and 'download'
    if action in ['delete', 'restore', 'download']:
        if not args:  # If no snapshot name is provided
            embed = discord.Embed(
                description=f':x: You must provide a snapshot name for the `{action}` command.',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

    # Process the commands if snapshot name is provided
    if action == 'delete':
        await bot_modules.delete_snapshot(ctx, bot, ' '.join(args))
    elif action == 'restore':
        await bot_modules.restore_snapshot(ctx, bot, server_running, ' '.join(args))
    elif action == 'download':
        await bot_modules.download_snapshot(ctx, bot, ' '.join(args))
    else:
        embed = discord.Embed(
            description=f':x: Unknown action `{action}`.',
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
    await bot_modules.verify(ctx, bot, server_running)


@bot.command(name='ping')
async def ping_command(ctx):
    await bot_modules.ping(ctx)


@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user.name}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,
                                                        name="over a Minecraft Server"))

if __name__ == "__main__":
    bot.run(TOKEN)
