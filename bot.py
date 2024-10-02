# version 1.3.0
import discord
from discord.ext import commands
import bot_modules
import subprocess
import requests
import time
import mcrcon
import configparser
import socket
import asyncio
import sqlite3
import random
import json
import os
import datetime
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
server_running = False
rcon_host = config.get('PythonConfig', 'rcon_host')
rcon_port = int(config.get('PythonConfig', 'rcon_port'))
rcon_password = config.get('PythonConfig', 'rcon_password')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)


def has_required_role(ctx):
    role = discord.utils.get(ctx.guild.roles, name=required_role)
    return role in ctx.author.roles


def has_operator(minecraft_username):
    try:
        with open('../ops.json', 'r') as file:
            if os.stat('../ops.json').st_size == 0:
                print("Error at 'has_operator': ops.json is empty.")
                return False

            ops_data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        print("Error at 'has_operator': Failed loading ops.json.")
        return False

    for op in ops_data:
        if op['name'] == minecraft_username:
            return True


def is_bot_owner(ctx):
    return ctx.author.id == bot_owner_id


@bot.command(name='start')
@commands.check(has_required_role)
async def start(ctx):
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
        public_ip = await get_public_ip()
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


@start.error
async def start_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        embed = discord.Embed(
            title="❌ Missing Role",
            description=f"You are missing the '{required_role}' role to start the server.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@bot.command(name='stop')
async def stop_command(ctx):
    discord_id = ctx.author.id
    c.execute("SELECT * FROM verification WHERE discord_id=?", (discord_id,))
    result = c.fetchone()
    if result is None:
        embed = discord.Embed(
            description=':x: You need to verify your Minecraft account first using the `$verify` command.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    minecraft_username = result[1]
    if not has_operator(minecraft_username) and not is_bot_owner(ctx):
        embed = discord.Embed(
            description=':x: You do not have permission to use this command.',
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
@commands.check(is_bot_owner)
async def shutdown_bot(ctx):
    embed = discord.Embed(description=':stop_button: Shutting down the bot...', color=discord.Color.red())
    await ctx.send(embed=embed)
    await bot.close()


@shutdown_bot.error
async def shutdown_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        embed = discord.Embed(
            title="❌ Missing Permissions",
            description="Only the Minecraft Server Owner can issue this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@bot.command(name='update')
@commands.check(is_bot_owner)
async def update_bot(ctx):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.github.com/repos/yuri010/minecraft-manager/releases/latest") as response:
            data = await response.json()
            latest_version = data.get("tag_name", "Unknown")

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


@update_bot.error
async def update_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        embed = discord.Embed(
            title="❌ Missing Permissions",
            description="Only the Minecraft Server Owner can issue this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)


@bot.command(name='info')
async def info_command(ctx, action=None):
    if action == 'snapshots':
        await info_snapshots(ctx)
    else:
        await info(ctx)


async def info(ctx):
    prefix = bot.command_prefix
    bot_user = bot.user
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.github.com/repos/yuri010/minecraft-manager/releases/latest") as response:
            data = await response.json()
            latest_version = data.get("tag_name", "Unknown")

    minecrafter_commands = [
        '`start`: Starts the Minecraft Server and displays the IP',
        '`status`: Shows the status of the Minecraft server',
        '`verify`: Link your Minecraft and Discord account (Required for some commands)'
    ]
    operator_commands = [
        '`snapshots <command>`: Manage world snapshots (see `info snapshots`)',
        '`console <command>`: Send commands to the Minecraft Server',
        '`stop`: Stops the Minecraft Server'
    ]
    bot_commands = [
        '`ping`: Pong!',
        '`info`: Display this info message'
    ]

    embed = discord.Embed(description=f"Hi! I am a simple Discord bot made by <@603158153638707242>.\nI am designed to\
                          manage Minecraft servers from within Discord.\n\nMy current prefix is: `{prefix}`",
                          color=discord.Color.green())
    embed.set_author(name='Minecraft Manager', icon_url=bot_user.avatar.url)
    embed.add_field(name='Minecrafter Commands', value='\n'.join(minecrafter_commands), inline=False)
    embed.add_field(name='Operator Commands', value='\n'.join(operator_commands), inline=False)
    embed.add_field(name='Miscellaneous Bot Commands', value='\n'.join(bot_commands), inline=False)
    update_indicator = "| 🔔 New version available!" if latest_version > BOT_VERSION else ""
    footer_text = f"Version {BOT_VERSION} | Sent at {timestamp} {update_indicator}"
    embed.set_footer(text=footer_text, icon_url=bot_user.avatar.url)
    await ctx.send(embed=embed)


async def info_snapshots(ctx):
    bot_user = bot.user
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    snapshot_commands = [
            '`list`: List all available snapshots',
            '`create <name>`: Create a new snapshot of the world',
            '`delete <name>`: Delete a snapshot',
            '`restore <name>`: Restore the server from a snapshot',
            '`download <name>`: Download a snapshot ("World download")'
    ]
    embed = discord.Embed(description="Here are the available snapshot management commands:",
                          color=discord.Color.green())
    embed.set_author(name='Minecraft Manager', icon_url=bot_user.avatar.url)
    embed.add_field(name='Snapshots Commands', value='\n'.join(snapshot_commands), inline=False)
    footer_text = f"Version {BOT_VERSION} | Sent at {timestamp}"
    embed.set_footer(text=footer_text, icon_url=bot_user.avatar.url)
    await ctx.send(embed=embed)


@bot.command(name='console')
async def console_command(ctx, *, command):
    discord_id = ctx.author.id
    c.execute("SELECT * FROM verification WHERE discord_id=?", (discord_id,))
    result = c.fetchone()
    if result is None:
        embed = discord.Embed(
            description=':x: You need to verify your Minecraft account first using the `$verify` command.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    minecraft_username = result[1]
    if not has_operator(minecraft_username) and not is_bot_owner(ctx):
        embed = discord.Embed(
            description=':x: You do not have permission to use this command.',
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


@bot.command(name='ping')
async def ping_command(ctx):
    start_time = time.time()
    message = await ctx.send('Pinging...')
    end_time = time.time()

    latency = (end_time - start_time) * 1000

    embed = discord.Embed(description=f'Pong! Latency: {latency:.2f} ms', color=discord.Color.green())
    await message.edit(content='', embed=embed)


@bot.command(name='status')
async def status_command(ctx):
    embed_color = discord.Color.red()
    public_ip = await get_public_ip() if server_running else None

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


async def get_public_ip():
    try:
        response = requests.get('http://localhost:4040/api/tunnels')
        response.raise_for_status()

        data = response.json()
        tunnels = data.get('tunnels', [])
        if tunnels:
            tunnel = tunnels[0]
            public_url = tunnel.get('public_url')
            return public_url
        else:
            return None
    except Exception as e:
        print(f"Failed to retrieve public IP: {str(e)}")
        return None


@bot.command(name='verify')
async def verify_command(ctx):
    if not server_running:
        embed = discord.Embed(description=':x: The Minecraft server is not running.', color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    discord_id = ctx.author.id
    c.execute("SELECT * FROM verification WHERE discord_id=?", (discord_id,))
    result = c.fetchone()

    if result:
        embed = discord.Embed(
            description=':warning: You are already verified. React with ✅ to restart verification or ❌ to abort.',
            color=discord.Color.orange()
        )
        message = await ctx.send(embed=embed)

        await message.add_reaction('✅')
        await message.add_reaction('❌')

        def check(reaction, user):
            return user == ctx.author and reaction.message.id == message.id and str(reaction.emoji) in ['✅', '❌']

        try:
            reaction, _ = await bot.wait_for('reaction_add', timeout=120, check=check)
        except asyncio.TimeoutError:
            embed = discord.Embed(
                description=':x: Verification process timed out.',
                color=discord.Color.red()
            )
            await message.edit(embed=embed)
            await message.clear_reactions()
            return

        if str(reaction.emoji) == '✅':
            await message.delete()
        else:
            embed = discord.Embed(
                description=':x: Verification process aborted.',
                color=discord.Color.red()
            )
            await message.edit(embed=embed)
            await message.clear_reactions()
            return

    embed = discord.Embed(
        description=':rocket: Verification process started. Please check your DMs.',
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

    dm_channel = await ctx.author.create_dm()
    embed = discord.Embed(
        description='Please join the Minecraft server and send your Minecraft username here.',
        color=discord.Color.blue()
    )
    await dm_channel.send(embed=embed)

    def check_author(m):
        return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

    try:
        message = await bot.wait_for('message', check=check_author, timeout=120)
        minecraft_username = message.content
    except asyncio.TimeoutError:
        embed = discord.Embed(
            description=':x: Verification process timed out.',
            color=discord.Color.red()
        )
        await dm_channel.send(embed=embed)
        return

    try:
        with mcrcon.MCRcon(rcon_host, rcon_password, port=rcon_port) as rcon:
            response = rcon.command('list')
    except mcrcon.MCRconException:
        embed = discord.Embed(
            description=':x: An error occurred while executing the "list" command in the Minecraft server.',
            color=discord.Color.red()
        )
        await dm_channel.send(embed=embed)
        return

    if minecraft_username not in response:
        embed = discord.Embed(
            description=':x: Your Minecraft username was not found online on the server. Please try again.',
            color=discord.Color.red()
        )
        await dm_channel.send(embed=embed)
        return

    verification_code = ''.join(random.choices('0123456789', k=6))

    try:
        with mcrcon.MCRcon(rcon_host, rcon_password, port=rcon_port) as rcon:
            rcon.command(f'w {minecraft_username} Discord verification code: {verification_code}')
    except mcrcon.MCRconException:
        embed = discord.Embed(
            description=':x: An error occurred while sending the verification code to the Minecraft server.',
            color=discord.Color.red()
        )
        await dm_channel.send(embed=embed)
        return

    embed = discord.Embed(
        description=':white_check_mark: A verification code has been sent to you in Minecraft.\
            Please enter it here to complete the verification process.',
        color=discord.Color.blue()
    )
    await dm_channel.send(embed=embed)

    try:
        message = await bot.wait_for('message', check=check_author, timeout=120)
        user_code = message.content
    except asyncio.TimeoutError:
        embed = discord.Embed(
            description=':x: Verification process timed out.',
            color=discord.Color.red()
        )
        await dm_channel.send(embed=embed)
        return

    if user_code != verification_code:
        embed = discord.Embed(
            description=':x: Incorrect verification code. Please try again.',
            color=discord.Color.red()
        )
        await dm_channel.send(embed=embed)
        return

    discord_id = ctx.author.id
    c.execute("INSERT OR REPLACE INTO verification VALUES (?, ?)", (discord_id, minecraft_username))
    conn.commit()

    embed = discord.Embed(
        description=':white_check_mark: Verification successful! Your Minecraft account has been linked.',
        color=discord.Color.green()
    )
    await dm_channel.send(embed=embed)


@bot.command(name='snapshots')
async def snapshots_command(ctx, action=None, *args):
    discord_id = ctx.author.id
    c.execute("SELECT * FROM verification WHERE discord_id=?", (discord_id,))
    result = c.fetchone()
    if result is None:
        embed = discord.Embed(
            description=':x: You need to verify your Minecraft account first using the `$verify` command.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    minecraft_username = result[1]

    if action == 'list' or action == 'download':
        if not has_required_role(ctx):
            embed = discord.Embed(
                description=':x: You do not have permission to use this command.',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

    if action == 'create':
        if not has_operator(minecraft_username):
            embed = discord.Embed(
                description=':x: You do not have permission to use this command.',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

    if action == 'delete' or action == 'restore':
        if not is_bot_owner(ctx):
            embed = discord.Embed(
                description=':x: You do not have permission to use this command.',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

    if action == 'create':
        await bot_modules.create_snapshot(ctx, bot, server_running, suppress_success_message=False)
    elif action == 'delete':
        await bot_modules.delete_snapshot(ctx, bot, ' '.join(args))
    elif action == 'restore':
        await bot_modules.restore_snapshot(ctx, bot, server_running, ' '.join(args))
    elif action == 'download':
        await bot_modules.download_snapshot(ctx, bot, ' '.join(args))
    else:
        await bot_modules.list_snapshots(ctx)


@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user.name}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,
                                                        name="over a Minecraft Server"))

if __name__ == "__main__":
    bot.run(TOKEN)
