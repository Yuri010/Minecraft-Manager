"""
verify.py

Version: 1.3.0

This module contains functionality for the verification process of users
linking their Discord and Minecraft accounts. It handles the entire
verification flow, including checking if the server is running,
sending and receiving verification codes, and updating the database
with the verified information.

Functions:
    - verify(ctx, bot): Manages the verification process,
      including sending DMs, handling user input, and updating the database.

Attributes:
    - RCON_HOST: The host address for the Minecraft server RCON.
    - RCON_PORT: The port for the Minecraft server RCON.
    - RCON_PASSWORD: The password for the Minecraft server RCON.
    - BOT_VERSION: The current version of the bot.

Notes:
    - The verification process requires that the Minecraft server is running.
    - Users must provide their Minecraft username, which is checked against
      the server's online players before verification.
    - The module uses the `mcrcon` library to interact with the Minecraft server.
"""


# Standard library imports
import asyncio
import configparser
import random
import sqlite3
from pathlib import Path

# Third-party imports
import discord
import mcrcon

# First-party imports
from bot_modules import utils


script_path = Path(__file__).resolve().parent
root_path = script_path.parent
db_path = root_path / 'minecraft_manager.db'
config_path = root_path / 'config.cfg'

conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS verification (
                discord_id INTEGER PRIMARY KEY,
                minecraft_name TEXT
            )''')

config = configparser.ConfigParser()
config.read(config_path)

RCON_HOST = config.get('PythonConfig', 'rcon_host')
RCON_PORT = int(config.get('PythonConfig', 'rcon_port'))
RCON_PASSWORD = config.get('PythonConfig', 'rcon_password')


async def verify(ctx, bot):
    if not bot.server_running:
        embed = discord.Embed(
            title=':x: Server Offline!',
            description='The Minecraft server is not running.',
            color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    discord_id = ctx.author.id
    c.execute("SELECT * FROM verification WHERE discord_id=?", (discord_id,))
    result = c.fetchone()

    if result:
        embed = discord.Embed(
            title=':warning: Already Verified!',
            description='You are already verified.\nReact with ✅ to restart verification or ❌ to abort.',
            color=discord.Color.orange()
        )
        message = await ctx.send(embed=embed)

        # Use the utility function to get user reaction
        reaction, _ = await utils.get_user_reaction(bot, message, ctx.author, ['✅', '❌'])

        if reaction is None:
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
        with mcrcon.MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as rcon:
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
        with mcrcon.MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as rcon:
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
        title=':white_check_mark: Success!',
        description='Verification successful! Your Minecraft account has been linked.',
        color=discord.Color.green()
    )
    await dm_channel.send(embed=embed)