# version 1.3.0
import discord
import datetime
import aiohttp

BOT_VERSION = "1.3.0"


async def info(ctx, bot):
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


async def info_snapshots(ctx, bot):
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