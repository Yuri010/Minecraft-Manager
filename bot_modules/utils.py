"""
utils.py

Version: 1.3.0

This module houses miscellaneous utility functions used by the Discord bot.
These functions provide various helper capabilities, such as retrieving the public
IP address and measuring the latency of commands.

Functions:
    - get_public_ip(): Asynchronously retrieves the public IP address from a local API.
    - ping(ctx): Sends a ping message to the Discord channel and measures the latency.

Notes:
    - The `get_public_ip()` function makes an HTTP request to a local server,
      and may fail if the server is not running or if there is no internet connection.
    - The `ping()` function calculates latency based on the time taken to send
      a message and receive the response, and it returns this value in milliseconds.
"""


# Standard library imports
import asyncio
import logging
import time
import json
import configparser
import socket
import sqlite3
from pathlib import Path

# Third-party imports
import discord
import requests


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

script_path = Path(__file__).resolve().parent
root_path = script_path.parent

conn = sqlite3.connect('minecraft_manager.db')
c = conn.cursor()

config = configparser.ConfigParser()
config.read('config.cfg')

REQUIRED_ROLE = config.get('PythonConfig', 'required_role')
BOT_OWNER_ID = int(config.get('PythonConfig', 'bot_owner_id'))


def check_server_running(host, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(3)  # Set a timeout for the connection
            result = sock.connect_ex((host, int(port)))  # Returns 0 if successful
            return result == 0  # Return True if successful
    except Exception as e:
        logging.error("Failed to connect to server at %d:%s - %d", host, port, e)
        return False


def check_server_latency(host, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(3)
            start_time = time.time()
            result = sock.connect_ex((host, port))
            end_time = time.time()

            if result == 0:
                return round((end_time - start_time) * 1000, 2)  # Return latency in ms
    except Exception as e:
        logging.error("Error while pinging server: %d", e)
        return None


async def get_public_ip():
    try:
        response = requests.get('http://localhost:4040/api/tunnels', timeout=5)  # Timeout after 5 seconds
        response.raise_for_status()

        data = response.json()
        tunnels = data.get('tunnels', [])
        if tunnels:
            tunnel = tunnels[0]
            public_url = tunnel.get('public_url')
            return public_url

        return None

    except Exception as e:
        logging.error("Failed to retrieve public IP: %s", e)
        return None


async def ping(ctx):
    start_time = time.time()
    message = await ctx.send('Pinging...')
    end_time = time.time()

    latency = (end_time - start_time) * 1000

    embed = discord.Embed(
        title=':ping_pong: Pong!',
        description=f'Latency: {latency:.2f} ms',
        color=discord.Color.green())
    await message.edit(content='', embed=embed)


def has_required_role(ctx):
    role = discord.utils.get(ctx.guild.roles, name=REQUIRED_ROLE)
    return role in ctx.author.roles


def has_operator(discord_id):
    try:
        # Check the database if the user has verified their Minecraft account
        c.execute("SELECT * FROM verification WHERE discord_id=?", (discord_id,))
        result = c.fetchone()

        if result is None:
            # User hasn't verified their Minecraft account
            logging.debug("'has_operator': User %d not verified.", discord_id)
            return False, 'You need to verify your Minecraft account first using the `$verify` command.'

        minecraft_username = result[1]

        ops_file = root_path.parent / 'ops.json'
        if not ops_file.exists():  # Check if the file exists at all
            logging.error("'has_operator': %s is missing.", ops_file)
            return False, f'Operator list is missing. Tried looking in {ops_file}'
        if ops_file.stat().st_size <= 2:  # Check if the file LEQ 2 bytes as it default with content `[]`
            logging.error("'has_operator': %s is empty.", ops_file)
            return False, 'You do not have operator permissions on the Minecraft server.'

        # Load the ops.json data
        with ops_file.open('r', encoding='utf-8') as file:
            ops_data = json.load(file)

        # Check if the Minecraft username is an operator
        for op in ops_data:
            if op['name'] == minecraft_username:
                return True, None  # User is an operator, no error message needed

        # If user is verified but not an operator
        return False, 'You do not have operator permissions on the Minecraft server.'

    except (FileNotFoundError, json.JSONDecodeError):
        logging.error("'has_operator': Failed loading %s.", ops_file)
        return False, 'Failed to load operator list.'


async def get_user_reaction(bot, message, user, valid_reactions, timeout=120):
    for reaction in valid_reactions:
        await message.add_reaction(reaction)

    def check(reaction, user_check):
        return user_check == user and str(reaction.emoji) in valid_reactions and reaction.message.id == message.id

    try:
        reaction, user_reaction = await bot.wait_for('reaction_add', timeout=timeout, check=check)
        return reaction, user_reaction
    except asyncio.TimeoutError:
        return None, None