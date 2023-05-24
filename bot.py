import discord
from discord.ext import commands
import subprocess
import requests
import time
import mcrcon

TOKEN = 'YOUR_BOT_TOKEN'
required_role = 'Minecrafter'
bot_owner_id = YOUR_OWNER_ID
server_running = False
rcon_host = '127.0.0.1'
rcon_port = 25575
rcon_password = 'RCON_PASS'

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='mc!', intents=intents)

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

        public_ip = await get_public_ip()
        if public_ip:
            public_ip = public_ip.replace('tcp://', '')  # Remove the "tcp://" prefix
            embed.description = ':white_check_mark: The Minecraft server has started successfully.'
            embed.description += f"\n\nThe server is now accessible at: **{public_ip}**"
            await message.edit(embed=embed)
        else:
            embed = discord.Embed(description='Failed to retrieve the public IP of the server.', color=discord.Color.red())
            await message.edit(embed=embed)
            
    except Exception as e:
        embed = discord.Embed(description=f':x: An error occurred while starting the server: {str(e)}', color=discord.Color.red())
        await message.edit(embed=embed)

@bot.command(name='shutdown')
@commands.check(is_bot_owner)
async def shutdown_bot(ctx):
    embed = discord.Embed(description=':stop_button: Shutting down the bot...', color=discord.Color.red())
    await ctx.send(embed=embed)
    await bot.close()

@bot.command(name='info')
async def info_command(ctx):
    prefix = bot.command_prefix
    bot_user = bot.user

    embed = discord.Embed(description=f"Hi! I am a simple Discord bot made by <@603158153638707242>.\nI am designed to manage Minecraft servers from within Discord.\n\nMy current prefix is: `{prefix}`", color=discord.Color.blue())
    embed.set_author(name=f'Minecraft Manager', icon_url=bot_user.avatar.url)
    embed.add_field(name='Commands', value='`start`: Starts the Minecraft Server and displays the IP\n`stop`: Stops the Minecraft Server\n`console <command>`: Send commands to the Minecraft Server\n`shutdown`: Shuts down the Discord bot\n`ping`: Pong!\n`info`: Display this info message', inline=False)

    await ctx.send(embed=embed)

@bot.command(name='console')
@commands.check(is_bot_owner)
async def console_command(ctx, *, command):
    if not server_running:
        embed = discord.Embed(description=':x: The Minecraft server is not running.', color=discord.Color.red())
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

@bot.command(name='ping')
async def ping_command(ctx):
    start_time = time.time()
    message = await ctx.send('Pinging...')
    end_time = time.time()

    latency = (end_time - start_time) * 1000  # Convert to milliseconds

    embed = discord.Embed(description=f'Pong! Latency: {latency:.2f} ms', color=discord.Color.green())
    await message.edit(content='', embed=embed)

@bot.command(name='stop')
@commands.check(is_bot_owner)
async def stop_command(ctx):
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

async def get_public_ip():
    time.sleep(30)

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

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user.name}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over a Minecraft Server"))

bot.run(TOKEN)
