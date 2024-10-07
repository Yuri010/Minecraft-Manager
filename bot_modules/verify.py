# version 1.3.0
# This file is where the verification magic happens

# Standard library imports
import asyncio
import configparser
import os
import random
import sqlite3

# Third-party imports
import discord
import mcrcon


script_path = os.path.dirname(os.path.abspath(__file__))
root_path = os.path.join(script_path, '..')
db_path = os.path.join(root_path, 'minecraft_manager.db')
config_path = os.path.join(root_path, 'config.cfg')

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


async def verify(ctx, bot, SERVER_RUNNING):
    if not SERVER_RUNNING:
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
        description=':white_check_mark: Verification successful! Your Minecraft account has been linked.',
        color=discord.Color.green()
    )
    await dm_channel.send(embed=embed)