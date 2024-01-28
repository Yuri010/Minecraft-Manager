# version 1.2.0
import discord
from discord.ext import commands
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
import zipfile
import shutil

conn = sqlite3.connect('verification.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS verification (
                discord_id INTEGER PRIMARY KEY,
                minecraft_name TEXT
            )''')

c.execute('''CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                path TEXT,
                file_size INTEGER,
                date TEXT,
                notes TEXT
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

    embed = discord.Embed(description=':rocket: Starting the Minecraft server, please wait...', color=discord.Color.blue())
    message = await ctx.send(embed=embed)

    try:
        subprocess.Popen('start cmd /c "start.bat -y"', shell=True)
        server_running = True
        await bot.change_presence(activity=discord.Game(name="a Minecraft Server"))

        await asyncio.sleep(45)
        public_ip = await get_public_ip()
        if public_ip:
            public_ip = public_ip.replace('tcp://', '')  # Remove the "tcp://" prefix
            embed = discord.Embed(
                title = ':white_check_mark: The Minecraft server has started successfully.',
                description = f"The server is now accessible at: **{public_ip}**",
                color=discord.Color.green()
            )
            await message.edit(embed=embed)
        else:
            embed = discord.Embed(description=':x: Failed to retrieve the public IP of the server.', color=discord.Color.red())
            await message.edit(embed=embed)

    except Exception as e:
        embed = discord.Embed(description=f':x: An error occurred while starting the server: {str(e)}', color=discord.Color.red())
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
    # Check if the user has verified their Minecraft account
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

    # Check if the user has operator privileges or is the owner
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
            response = rcon.command('stop')
            embed = discord.Embed(description=':stop_button: Sent the `stop` command to the Minecraft server.', color=discord.Color.green())
            await ctx.send(embed=embed)
    except mcrcon.MCRconException as e:
        embed = discord.Embed(description=':x: Failed to send the `stop` command to the Minecraft server.', color=discord.Color.red())
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
            description=f"Only the Minecraft Server Owner can issue this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name='info')
async def info_command(ctx):
    prefix = bot.command_prefix
    bot_user = bot.user

    # Minecraft Server Commands
    minecraft_commands = [
        '`start`: Starts the Minecraft Server and displays the IP',
        '`stop`: Stops the Minecraft Server',
        '`console <command>`: Send commands to the Minecraft Server',
        '`status`: Shows the status of the Minecraft server',
        '`verify`: Link your Minecraft and Discord account (Required for some commands)'
    ]

    # Miscellaneous Bot Commands
    bot_commands = [
        '`ping`: Pong!',
        '`info`: Display this info message',
        '`shutdown`: Shuts down the Discord bot'
    ]

    embed = discord.Embed(description=f"Hi! I am a simple Discord bot made by <@603158153638707242>.\nI am designed to manage Minecraft servers from within Discord.\n\nMy current prefix is: `{prefix}`", color=discord.Color.blue())
    embed.set_author(name=f'Minecraft Manager', icon_url=bot_user.avatar.url)
    embed.add_field(name='Minecraft Server Commands', value='\n'.join(minecraft_commands), inline=False)
    embed.add_field(name='Miscellaneous Bot Commands', value='\n'.join(bot_commands), inline=False)

    await ctx.send(embed=embed)

@bot.command(name='console')
async def console_command(ctx, *, command):
    # Check if the user has verified their Minecraft account
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

    # Check if the user has operator privileges
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
            embed = discord.Embed(title='Minecraft Console', description=f'Command: {command}', color=discord.Color.green())
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

    latency = (end_time - start_time) * 1000  # Convert to milliseconds

    embed = discord.Embed(description=f'Pong! Latency: {latency:.2f} ms', color=discord.Color.green())
    await message.edit(content='', embed=embed)

@bot.command(name='status')
async def status_command(ctx):
    embed_color = discord.Color.red()  # Default color for stopped status
    public_ip = await get_public_ip() if server_running else None

    if server_running:
        embed_color = discord.Color.green()  # Color for running status
        try:
            host, port = public_ip.replace('tcp://', '').split(':')[:2] if ':' in public_ip else (public_ip, '25565')

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(3)  # Set a timeout for the socket connection
                result = sock.connect_ex((host, int(port)))

            if result != 0:
                embed_color = discord.Color.red()  # Update color to red if the port is closed
        except Exception as e:
            print(f'Failed to check server status: {str(e)}')

    embed = discord.Embed(title='Server Status', color=embed_color)
    embed.add_field(name='Status', value='Running' if server_running else 'Stopped', inline=False)
    embed.add_field(name='IP', value=public_ip.replace('tcp://', '') if server_running else 'N/A', inline=False)

    if server_running:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(3)  # Set a timeout for the socket connection
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

    # Check if the user is already verified
    discord_id = ctx.author.id
    c.execute("SELECT * FROM verification WHERE discord_id=?", (discord_id,))
    result = c.fetchone()

    if result:
        # User is already verified, prompt to restart or abort
        embed = discord.Embed(
            description=':warning: You are already verified. React with ✅ to restart verification or ❌ to abort.',
            color=discord.Color.orange()
        )
        message = await ctx.send(embed=embed)

        # Add reactions
        await message.add_reaction('✅')
        await message.add_reaction('❌')

        # Wait for reaction
        def check(reaction, user):
            return user == ctx.author and reaction.message.id == message.id and str(reaction.emoji) in ['✅', '❌']

        try:
            reaction, _ = await bot.wait_for('reaction_add', timeout=120, check=check)
        except asyncio.TimeoutError:
            embed = discord.Embed(
                description=':x: Verification process timed out.',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        if str(reaction.emoji) == '✅':
            # Restart verification
            await message.delete()
        else:
            # Abort verification
            embed = discord.Embed(
                description=':x: Verification process aborted.',
                color=discord.Color.red()
            )
            await message.edit(embed=embed)
            return

    # Send a message in the server channel to start the verification process
    embed = discord.Embed(
        description=':rocket: Verification process started. Please check your DMs.',
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

    # Prompt the user to join the Minecraft server
    dm_channel = await ctx.author.create_dm()
    embed = discord.Embed(
        description='Please join the Minecraft server and send your Minecraft username here.',
        color=discord.Color.blue()
    )
    await dm_channel.send(embed=embed)

    # Wait for the user's DM with their Minecraft username
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

    # Execute the "list" command in the Minecraft server using MCRCON
    try:
        with mcrcon.MCRcon(rcon_host, rcon_password, port=rcon_port) as rcon:
            response = rcon.command('list')
    except mcrcon.MCRconException as e:
        embed = discord.Embed(
            description=':x: An error occurred while executing the "list" command in the Minecraft server.',
            color=discord.Color.red()
        )
        await dm_channel.send(embed=embed)
        return

    # Check if the user's Minecraft username is in the response
    if minecraft_username not in response:
        embed = discord.Embed(
            description=':x: Your Minecraft username was not found online on the server. Please try again.',
            color=discord.Color.red()
        )
        await dm_channel.send(embed=embed)
        return

    # Generate a random verification code
    verification_code = ''.join(random.choices('0123456789', k=6))

    # Whisper the verification code to the user using MCRCON
    try:
        with mcrcon.MCRcon(rcon_host, rcon_password, port=rcon_port) as rcon:
            rcon.command(f'w {minecraft_username} Discord verification code: {verification_code}')
    except mcrcon.MCRconException as e:
        embed = discord.Embed(
            description=':x: An error occurred while sending the verification code to the Minecraft server.',
            color=discord.Color.red()
        )
        await dm_channel.send(embed=embed)
        return

    # Wait for the user's DM with the verification code
    embed = discord.Embed(
        description=':white_check_mark: A verification code has been sent to you in Minecraft. Please enter it here to complete the verification process.',
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

    # Check if the verification code matches
    if user_code != verification_code:
        embed = discord.Embed(
            description=':x: Incorrect verification code. Please try again.',
            color=discord.Color.red()
        )
        await dm_channel.send(embed=embed)
        return

    # Add the user's Minecraft username and Discord ID to the database
    discord_id = ctx.author.id
    c.execute("INSERT OR REPLACE INTO verification VALUES (?, ?)", (discord_id, minecraft_username))
    conn.commit()

    embed = discord.Embed(
        description=':white_check_mark: Verification successful! Your Minecraft account has been linked.',
        color=discord.Color.green()
    )
    await dm_channel.send(embed=embed)

def has_operator(minecraft_username):
    with open('ops.json', 'r') as file:
        ops_data = json.load(file)
        for op in ops_data:
            if op['name'] == minecraft_username:
                return True
    return False

@bot.command(name='snapshots')
async def snapshots_command(ctx, action=None):
    if action == 'create':
        await create_snapshot(ctx)
    else:
        await list_snapshots(ctx)

async def list_snapshots(ctx):
    c.execute("SELECT * FROM snapshots")
    snapshots = c.fetchall()

    if not snapshots:
        embed = discord.Embed(description='No snapshots available.', color=discord.Color.blue())
    else:
        embed = discord.Embed(title='World Snapshots', color=discord.Color.blue())
        for snapshot in snapshots:
            embed.add_field(name=f'Snapshot {snapshot[0]}', value=f'**Date:** {snapshot[4]}\n**Notes:** {snapshot[5]}', inline=False)

    await ctx.send(embed=embed)

async def create_snapshot(ctx):
    # Check if the server is running
    if server_running:
        embed = discord.Embed(description=':x: Cannot create a snapshot while the server is running.', color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Gather snapshot metadata from the user
    embed = discord.Embed(title='Please provide metadata for the snapshot.', color=discord.Color.blue())
    embed.add_field(name='Notes', value='Enter a note or description for this snapshot.', inline=False)
    await ctx.send(embed=embed) 

    def check_author(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    #embed = discord.Embed(description=':x: Snapshot function not yet implemented.', color=discord.Color.red())
    #await ctx.send(embed=embed)
    #return

    temp_folder = "temp_snapshot"
    os.makedirs(temp_folder, exist_ok=True)

    try:
        # Copy world folders to the temporary folder
        world_folders = ["world", "world_nether", "world_the_end"]
        for folder in world_folders:
            shutil.copytree(os.path.join("..", folder), os.path.join(temp_folder, folder))

        # Compress the snapshot
        snapshot_filename = f"snapshot_{int(time.time())}.zip"
        snapshot_path = os.path.join("scripts\snapshots", snapshot_filename)
        with zipfile.ZipFile(snapshot_path, 'w') as snapshot_zip:
            for folder in world_folders:
                snapshot_zip.write(os.path.join(temp_folder, folder), arcname=folder, compress_type=zipfile.ZIP_DEFLATED)

        # Get the file size
        file_size = os.path.getsize(snapshot_path)

        # Add snapshot metadata to the database
        current_date = time.strftime('%Y-%m-%d %H:%M:%S')
        c.execute("INSERT INTO snapshots (filename, path, file_size, date, notes) VALUES (?, ?, ?, ?, ?)",
                  (snapshot_filename, snapshot_path, file_size, current_date))
        conn.commit()

        embed = discord.Embed(description=':white_check_mark: Snapshot created successfully.', color=discord.Color.green())
        await ctx.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(description=f':x: Failed to create snapshot: {str(e)}', color=discord.Color.red())
        await ctx.send(embed=embed)

    finally:
        # Clean up: Remove the temporary folder
        shutil.rmtree(temp_folder, ignore_errors=True)

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user.name}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over a Minecraft Server"))

bot.run(TOKEN)