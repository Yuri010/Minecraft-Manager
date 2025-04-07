"""
snapshots.py

Version: 1.3.0

This module houses all logic for managing Minecraft world snapshots within
the Discord bot. It includes functions to create, list, restore, delete,
and download snapshots, allowing users to manage their Minecraft server
worlds effectively.

Functions:
    - get_snapshot(ctx, snapshot_name): (Internal) Fetches a snapshot from the database.
    - list_snapshots(ctx): Fetches and displays a list of all snapshots.
    - create_snapshot(ctx, bot, suppress_success_message):
      Creates a new snapshot of the world, handling user input and warnings.
    - delete_snapshot(ctx, bot, snapshot_name): Deletes a specified snapshot
      after user confirmation.
    - restore_snapshot(ctx, bot, snapshot_name): Restores the
      server from a specified snapshot, creating a new snapshot beforehand.
    - download_snapshot(ctx, snapshot_name): Downloads a specified snapshot
      to the Discord channel.

Attributes:
    - db_path: The path to the SQLite database for snapshot management.
    - conn: The SQLite connection to the database.
    - c: The cursor object for executing SQL commands.

Notes:
    - The module interacts with the SQLite database to store snapshot details.
    - It uses Discord's embed functionality to communicate with users in
      a visually appealing manner.
    - Ensure the Minecraft server is not running when creating or restoring snapshots.
"""


# Standard library imports
import asyncio
import shutil
import sqlite3
import time
from pathlib import Path

# Third-party imports
import discord

# First-party imports
from bot_modules import utils


script_path = Path(__file__).resolve().parent
root_path = script_path.parent

db_path = root_path / 'minecraft_manager.db'
conn = sqlite3.connect(db_path)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                fancy_name TEXT,
                path TEXT,
                file_size INTEGER,
                date TEXT,
                notes TEXT
            )''')


async def get_snapshot(ctx, snapshot_name):
    c.execute("SELECT * FROM snapshots WHERE fancy_name=?", (snapshot_name,))
    snapshot = c.fetchone()

    if not snapshot:
        embed = discord.Embed(
            title=':x: Not Found',
            description=f'Snapshot with the name "{snapshot_name}" not found.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return None

    return snapshot


async def list_snapshots(ctx):
    c.execute("SELECT * FROM snapshots")
    snapshots = c.fetchall()

    normal_embed = discord.Embed(color=discord.Color.green())
    excluded_entries = []

    for snapshot in snapshots:
        file_path = Path(snapshot[3])

        if not file_path.exists():
            excluded_entries.append(snapshot[0])
            continue

        file_size_mb = round(snapshot[4] / (1024 * 1024), 2)
        normal_embed.add_field(
            name=f'{snapshot[1]} - {snapshot[2]}',
            value=f'**Date:** {snapshot[5]}\n**File Size:** {file_size_mb} MB\n**Notes:** {snapshot[6]}',
            inline=False
        )

    if excluded_entries:
        c.executemany("DELETE FROM snapshots WHERE id=?", [(entry_id,) for entry_id in excluded_entries])
        conn.commit()
        normal_embed.set_footer(text=f"Removed {len(excluded_entries)} entries that could not be found.", icon_url="")

    normal_embed.title = '📸 World Snapshots'

    if normal_embed.fields:
        await ctx.send(embed=normal_embed)
    else:
        normal_embed.description = 'No snapshots available.'
        await ctx.send(embed=normal_embed)


async def create_snapshot(ctx, bot, *args):
    if bot.server_running:
        embed = discord.Embed(
            title=':x: Server Running!',
            description='Cannot create a snapshot while the server is running.',
            color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Check if the main "world" folder exists
    main_world_folder = root_path.parent / "world"
    if not main_world_folder.exists():
        embed = discord.Embed(
            title=':x: Out of this world!',
            description='The main world folder does not exist. Aborting snapshot creation.',
            color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Join all arguments into a single string
    args_str = ' '.join(args)

    # Split name and description using "|" as the delimiter
    if '|' in args_str:
        snapshot_name, snapshot_description = map(str.strip, args_str.split('|', 1))
    else:
        snapshot_name = args_str.strip()
        snapshot_description = None

    def check_author(m):
        return m.author == ctx.author and m.channel == ctx.channel

    # Ask for a snapshot name in case that isn't provided (Prompted Creation)
    if not snapshot_name:
        embed = discord.Embed(
            title=':pencil: Snapshot Creation',
            description='Please provide a name for this snapshot.',
            color=discord.Color.blue()
        )
        question = await ctx.send(embed=embed)

        try:
            answer = await bot.wait_for('message', check=check_author, timeout=120)
            snapshot_name = answer.content.strip()  # Strip any extra spaces

            # Clean up the user's message
            await answer.delete()

        except asyncio.TimeoutError:
            snapshot_name = f"Snapshot {int(time.time())}"

        await question.delete()  # Clean up the request embed

    # Check if a snapshot with the given name doesn't exist already
    c.execute("SELECT * FROM snapshots WHERE fancy_name=?", (snapshot_name,))
    if c.fetchone() is not None:
        embed = discord.Embed(
            title=':x: Already Exists!',
            description=f'A snapshot with the name "{snapshot_name}" already exists. Snapshot aborted.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # If no description provided, prompt the user for it
    if snapshot_description is None:
        embed = discord.Embed(
            title=':pencil: Snapshot Creation',
            description='Please provide a description for this snapshot.',
            color=discord.Color.blue()
        )
        question = await ctx.send(embed=embed)

        try:
            answer = await bot.wait_for('message', check=check_author, timeout=120)
            snapshot_description = answer.content.strip()

            await answer.delete()  # Clean up user's message

        except asyncio.TimeoutError:
            snapshot_description = ""  # Default description if timeout

        await question.delete()  # Clean up description prompt

    # Proceed with snapshot creation logic
    embed = discord.Embed(
        title=':rocket: Snapshot Creation',
        description=f'Creating snapshot "{snapshot_name}"...\n',
        color=discord.Color.blue()
    )
    waitembed = await ctx.send(embed=embed)

    temp_folder = Path("temp_snapshot")
    temp_folder.mkdir(exist_ok=True)

    try:
        snapshots_folder = root_path / "snapshots"
        world_folders = ["world", "world_nether", "world_the_end"]
        skipped_folders = []

        for folder in world_folders:
            source_folder = root_path.parent / folder
            destination_folder = temp_folder / folder

            if source_folder.exists():
                shutil.copytree(str(source_folder), str(destination_folder))
            else:
                skipped_folders.append(folder)

        # Draft a success message
        embed = discord.Embed(
            title=':white_check_mark: Snapshot Created!',
            description=f'Snapshot "{snapshot_name}" created successfully.',
            color=discord.Color.green()
        )

        # Set message for skipped folders
        if skipped_folders:
            skipped_folders_text = "\n".join([f':warning: Skipped folder "{folder}" as it does not exist.'
                                             for folder in skipped_folders])
            embed.description += f'\n\n{skipped_folders_text}'  # Add skipped folder notifications

        snapshot_filename = f"snapshot_{int(time.time())}"
        snapshot_path = snapshots_folder / snapshot_filename

        shutil.make_archive(str(snapshot_path), 'zip', str(temp_folder))
        file_size = snapshot_path.with_suffix('.zip').stat().st_size
        current_date = time.strftime('%Y-%m-%d %H:%M:%S')

        c.execute("INSERT INTO snapshots(filename, fancy_name, path, file_size, date, notes) VALUES (?, ?, ?, ?, ?, ?)",
                  (f"{snapshot_filename}.zip", snapshot_name, str(snapshot_path.with_suffix('.zip')),
                   file_size, current_date, snapshot_description))
        conn.commit()

        await waitembed.edit(embed=embed)  # Send success message

    except Exception as e:
        embed = discord.Embed(
            title=":x: Snapshot Failed!",
            description=f'Failed to create snapshot: {str(e)}',
            color=discord.Color.red()
        )
        await waitembed.edit(embed=embed)

    finally:
        shutil.rmtree(temp_folder, ignore_errors=True)


async def delete_snapshot(ctx, bot, snapshot_name):
    snapshot = await get_snapshot(ctx, snapshot_name)
    if not snapshot:
        return

    snapshot_id = snapshot[0]
    fancy_name = snapshot[2]
    file_path = Path(snapshot[3])

    embed = discord.Embed(
        title=':warning: Snapshot Deletion',
        description=f'Are you sure you want to delete the snapshot "{fancy_name}"?',
        color=discord.Color.yellow()
    )

    message = await ctx.send(embed=embed)

    # Use the utility function to get user reaction
    reaction, _ = await utils.get_user_reaction(bot, message, ctx.author, ['✅', '❌'])

    if reaction is None:
        embed = discord.Embed(
            description=f':x: Snapshot deletion process timed out for "{fancy_name}".',
            color=discord.Color.red()
        )
        await message.edit(embed=embed)
        await message.clear_reactions()
        return

    if str(reaction.emoji) == '✅':
        file_path.unlink()  # Use Path.unlink() to delete the file
        c.execute("DELETE FROM snapshots WHERE id=?", (snapshot_id,))
        conn.commit()

        embed = discord.Embed(
            title=':wastebasket: Snapshot Deleted',
            description=f'Snapshot "{fancy_name}" has been deleted.',
            color=discord.Color.green()
        )
        await message.edit(embed=embed)
        await message.clear_reactions()
    else:
        embed = discord.Embed(
            title=':x: Snapshot Deletion',
            description=f'Snapshot deletion process aborted for "{fancy_name}".',
            color=discord.Color.red()
        )
        await message.edit(embed=embed)
        await message.clear_reactions()


async def restore_snapshot(ctx, bot, snapshot_name):
    if bot.server_running:
        embed = discord.Embed(
            title=':x: Server Running!',
            description='Cannot restore a snapshot while the server is running.',
            color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Fetch the snapshot from the database
    snapshot = await get_snapshot(ctx, snapshot_name)
    if not snapshot:
        return

    fancy_name = snapshot[2]
    snapshot_path = Path(snapshot[3])

    # Prompt user for confirmation before restoring
    embed = discord.Embed(
        title=':tools: Restore Snapshot',
        description=f'Are you sure you want to restore the snapshot "{fancy_name}"?\n\
                      This will create a new snapshot before restoring and overwrite the current world data.',
        color=discord.Color.yellow()
    )
    message = await ctx.send(embed=embed)

    # Use the utility function to handle reactions
    reaction, _ = await utils.get_user_reaction(bot, message, ctx.author, ['✅', '❌'])

    if reaction is None:
        embed = discord.Embed(
            description=f':x: Snapshot restoration process timed out for "{fancy_name}".',
            color=discord.Color.red()
        )
        await message.edit(embed=embed)
        await message.clear_reactions()
        return

    if str(reaction.emoji) == '✅':
        await create_snapshot(ctx, bot)
        await message.delete()

        # Prepare embed to update during the process
        embed = discord.Embed(
            description=f':rocket: Restoring snapshot "{fancy_name}"...\n',
            color=discord.Color.blue()
        )
        message = await ctx.send(embed=embed)

        world_folders = ["world", "world_nether", "world_the_end"]
        temp_folder = Path("temp_restore")
        temp_folder.mkdir(exist_ok=True)

        try:
            # Unpack the snapshot archive
            shutil.unpack_archive(str(snapshot_path), str(temp_folder))

            # Check if the main "world" folder exists in the snapshot
            main_world_folder = temp_folder / "world"
            if not main_world_folder.exists():
                embed = discord.Embed(
                    title=':x: Snapshot Restoring Failed!',
                    description='The main world folder is missing from the snapshot. Aborting restore.',
                    color=discord.Color.red()
                )
                await message.edit(embed=embed)
                shutil.rmtree(temp_folder, ignore_errors=True)
                return

            skipped_folders = []
            for folder in world_folders:
                source_folder = temp_folder / folder
                dest_folder = root_path.parent / folder

                if source_folder.exists():
                    # Remove the old folder and replace it
                    shutil.rmtree(dest_folder, ignore_errors=True)
                    shutil.move(str(source_folder), str(dest_folder))
                else:
                    skipped_folders.append(folder)

            # Draft an embed with success message
            embed = discord.Embed(
                title=':white_check_mark: Snapshot Restored!',
                description=f'Snapshot "{fancy_name}" has been successfully restored.',
                color=discord.Color.green()
            )

            # Set message for skipped folders
            if skipped_folders:
                skipped_folders_text = "\n".join([f':warning: Skipping folder "{folder}"\
                                                  as it was not found in the snapshot.' for folder in skipped_folders])
                embed.description += f'\n\n{skipped_folders_text}'  # Add skipped folder notifications

            shutil.rmtree(temp_folder, ignore_errors=True)

            await message.edit(embed=embed)  # Send Success Message

        except Exception as e:
            # Catch all exceptions and report them in Discord
            embed = discord.Embed(
                title=':x: Snapshot Restoring Failed!',
                description=f'Failed to restore snapshot: {str(e)}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            shutil.rmtree(temp_folder, ignore_errors=True)
    else:
        embed = discord.Embed(
            title=':x: Restore Snapshot Aborted!',
            description=f'Snapshot restoration process aborted for "{fancy_name}".',
            color=discord.Color.red()
        )
        await message.edit(embed=embed)
        await message.clear_reactions()


async def download_snapshot(ctx, snapshot_name):
    snapshot = await get_snapshot(ctx, snapshot_name)
    if not snapshot:
        return

    snapshot_path = Path(snapshot[3])
    if not snapshot_path.exists():
        embed = discord.Embed(
            title=':x: Not Found',
            description=f'Snapshot file for "{snapshot_name}" not found.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    embed = discord.Embed(
        title=':hourglass: Uploading Snapshot...',
        description=f'Starting upload for snapshot "{snapshot_name}", please wait...',
        color=discord.Color.blue()
        )
    message = await ctx.send(embed=embed)

    try:
        file = discord.File(str(snapshot_path), filename=snapshot_path.name)

        embed = discord.Embed(
            title=':cloud: Snapshot Uploaded',
            description=f'Snapshot "{snapshot_name}" has been successfully uploaded.',
            color=discord.Color.green()
        )
        await ctx.send(embed=embed, file=file)
        await message.delete()

    except Exception as e:
        embed = discord.Embed(
            title=':x: Snapshot Upload Failed!',
            description=f'Failed to upload snapshot "{snapshot_name}": {str(e)}',
            color=discord.Color.red()
        )
        await message.edit(embed=embed)