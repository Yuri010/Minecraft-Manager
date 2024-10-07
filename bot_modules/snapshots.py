"""
snapshots.py

Version: 1.3.0

This module houses all logic for managing Minecraft world snapshots within
the Discord bot. It includes functions to create, list, restore, delete,
and download snapshots, allowing users to manage their Minecraft server
worlds effectively.

Functions:
    - list_snapshots(ctx): Fetches and displays a list of all snapshots.
    - create_snapshot(ctx, bot, server_running, suppress_success_message):
      Creates a new snapshot of the world, handling user input and warnings.
    - delete_snapshot(ctx, bot, snapshot_name): Deletes a specified snapshot
      after user confirmation.
    - restore_snapshot(ctx, bot, server_running, snapshot_name): Restores the
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


# Get the absolute path of the script
script_path = Path(__file__).resolve().parent

# Define the root directory (parent of the "scripts" folder)
root_path = script_path.parent

# Path to the SQLite database
db_path = root_path / 'minecraft_manager.db'

# Database connection
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Create the snapshots table if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                fancy_name TEXT,
                path TEXT,
                file_size INTEGER,
                date TEXT,
                notes TEXT
            )''')


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


async def create_snapshot(ctx, bot, server_running, suppress_success_message):
    if server_running:
        embed = discord.Embed(description=':x: Cannot create a snapshot while the server is running.',
                              color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Check if the main "world" folder exists
    main_world_folder = root_path.parent / "world"
    if not main_world_folder.exists():
        embed = discord.Embed(description=':x: The main world folder does not exist. Aborting snapshot creation.',
                              color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Create a consolidated status embed to ask for the snapshot name
    embed = discord.Embed(
        description='📝 Please provide a name for this snapshot.',
        color=discord.Color.blue()
    )
    waitembed = await ctx.send(embed=embed)

    def check_author(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        # Wait for the user to respond with the snapshot name
        name_a = await bot.wait_for('message', check=check_author, timeout=120)
        snapshot_name = name_a.content.strip()  # Strip any extra spaces

        # Delete the user's message to clean up chat
        await name_a.delete()

    except asyncio.TimeoutError:
        snapshot_name = f"Snapshot {int(time.time())}"

    # Check if the snapshot name already exists in the database
    c.execute("SELECT * FROM snapshots WHERE fancy_name=?", (snapshot_name,))
    if c.fetchone() is not None:
        embed = discord.Embed(
            description=f':x: A snapshot with the name "{snapshot_name}" already exists.\
                Please choose a different name.',
            color=discord.Color.red()
        )
        await waitembed.edit(embed=embed)
        return

    # Ask for the description and update the embed
    embed.description = '📝 Please provide a description for this snapshot.'
    await waitembed.edit(embed=embed)

    try:
        # Wait for the user to respond with the snapshot description
        desc_a = await bot.wait_for('message', check=check_author, timeout=120)
        snapshot_description = desc_a.content.strip()  # Strip any extra spaces

        # Delete the user's message to clean up chat
        await desc_a.delete()

    except asyncio.TimeoutError:
        snapshot_description = ""

    # Update the embed to indicate snapshot creation is starting
    embed.title = ':rocket: Creating snapshot...'
    embed.description = f'Snapshot name: **{snapshot_name}**\n'
    waitembed = await ctx.send(embed=embed)

    # Prepare the temp folder for the snapshot
    temp_folder = Path("temp_snapshot")
    temp_folder.mkdir(exist_ok=True)

    try:
        snapshots_folder = root_path / "snapshots"

        # World folders to back up
        world_folders = ["world", "world_nether", "world_the_end"]
        skipped_folders = []

        for folder in world_folders:
            source_folder = root_path.parent / folder  # Folder to be backed up
            destination_folder = temp_folder / folder  # Temp folder for backup

            if source_folder.exists():
                shutil.copytree(str(source_folder), str(destination_folder))
            else:
                skipped_folders.append(folder)

        # Update embed with warnings about skipped folders
        if skipped_folders:
            skipped_folders_text = "\n".join([f':warning: Skipped folder "{folder}" as it does not exist.'
                                             for folder in skipped_folders])
            embed.description += f'\n{skipped_folders_text}'

        # Create the snapshot archive
        snapshot_filename = f"snapshot_{int(time.time())}"
        snapshot_path = snapshots_folder / snapshot_filename

        shutil.make_archive(str(snapshot_path), 'zip', str(temp_folder))

        file_size = snapshot_path.with_suffix('.zip').stat().st_size
        current_date = time.strftime('%Y-%m-%d %H:%M:%S')

        # Save the snapshot details to the database
        c.execute("INSERT INTO snapshots(filename, fancy_name, path, file_size, date, notes) VALUES (?, ?, ?, ?, ?, ?)",
                  (f"{snapshot_filename}.zip", snapshot_name, str(snapshot_path.with_suffix('.zip')),
                   file_size, current_date, snapshot_description))
        conn.commit()

        # Update the embed to show the snapshot was successfully created
        embed.title = '✅ Snapshot Creation Finished'
        embed.description += f'\n:white_check_mark: Snapshot "{snapshot_name}" created successfully.'
        embed.color = discord.Color.green()
        await waitembed.edit(embed=embed)

    except Exception as e:
        # Catch all exceptions and report them in Discord
        embed.title = '❌ Snapshot Creation Finished with Errors'
        embed.description = f':x: Failed to create snapshot: {str(e)}'
        embed.color = discord.Color.red()
        await waitembed.edit(embed=embed)

    finally:
        shutil.rmtree(temp_folder, ignore_errors=True)
        if suppress_success_message:
            await waitembed.delete()


async def delete_snapshot(ctx, bot, snapshot_name):
    c.execute("SELECT * FROM snapshots WHERE fancy_name=?", (snapshot_name,))
    snapshot = c.fetchone()

    if not snapshot:
        embed = discord.Embed(
            description=f':x: Snapshot with the name "{snapshot_name}" not found.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    snapshot_id, fancy_name, path = snapshot
    file_path = Path(path)

    delete_embed = discord.Embed(
        description=f':warning: Are you sure you want to delete the snapshot "{fancy_name}"?',
        color=discord.Color.yellow()
    )

    delete_message = await ctx.send(embed=delete_embed)

    def check_delete(reaction, user):
        return user == ctx.author and reaction.message.id == delete_message.id and str(reaction.emoji) in ['✅', '❌']

    await delete_message.add_reaction('✅')
    await delete_message.add_reaction('❌')

    try:
        reaction, _ = await bot.wait_for('reaction_add', timeout=120, check=check_delete)
    except asyncio.TimeoutError:
        embed = discord.Embed(
            description=f':x: Snapshot deletion process timed out for "{fancy_name}".',
            color=discord.Color.red()
        )
        await delete_message.edit(embed=embed)
        await delete_message.clear_reactions()
        return

    if str(reaction.emoji) == '✅':
        file_path.unlink()  # Use Path.unlink() to delete the file
        c.execute("DELETE FROM snapshots WHERE id=?", (snapshot_id,))
        conn.commit()

        embed = discord.Embed(
            description=f':wastebasket: Snapshot "{fancy_name}" has been deleted.',
            color=discord.Color.green()
        )
        await delete_message.edit(embed=embed)
        await delete_message.clear_reactions()
    else:
        embed = discord.Embed(
            description=f':x: Snapshot deletion process aborted for "{fancy_name}".',
            color=discord.Color.red()
        )
        await delete_message.edit(embed=embed)
        await delete_message.clear_reactions()


async def restore_snapshot(ctx, bot, server_running, snapshot_name):
    if server_running:
        embed = discord.Embed(description=':x: Cannot restore a snapshot while the server is running.',
                              color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    # Fetch the snapshot from the database
    c.execute("SELECT * FROM snapshots WHERE fancy_name=?", (snapshot_name,))
    snapshot = c.fetchone()

    if not snapshot:
        embed = discord.Embed(
            description=f':x: Snapshot with the name "{snapshot_name}" not found.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    fancy_name, path = snapshot
    snapshot_path = Path(path)

    # Prompt user for confirmation before restoring
    confirm_embed = discord.Embed(
        description=f'🛠️ Are you sure you want to restore the snapshot "{fancy_name}"?\n'
                    f'This will create a new snapshot before restoring and overwrite the current world data.',
        color=discord.Color.yellow()
    )
    confirm_message = await ctx.send(embed=confirm_embed)

    def check_reaction(reaction, user):
        return user == ctx.author and reaction.message.id == confirm_message.id and str(reaction.emoji) in ['✅', '❌']

    await confirm_message.add_reaction('✅')
    await confirm_message.add_reaction('❌')

    try:
        reaction, _ = await bot.wait_for('reaction_add', timeout=120, check=check_reaction)
    except asyncio.TimeoutError:
        embed = discord.Embed(
            description=f':x: Snapshot restoration process timed out for "{fancy_name}".',
            color=discord.Color.red()
        )
        await confirm_message.edit(embed=embed)
        await confirm_message.clear_reactions()
        return

    if str(reaction.emoji) == '✅':
        await create_snapshot(ctx, bot, server_running, suppress_success_message=True)
        await confirm_message.delete()

        # Prepare embed to update during the process
        embed = discord.Embed(
            description=f':rocket: Restoring snapshot "{fancy_name}"...\n',
            color=discord.Color.blue()
        )
        waitembed = await ctx.send(embed=embed)

        world_folders = ["world", "world_nether", "world_the_end"]
        temp_folder = Path("temp_restore")
        temp_folder.mkdir(exist_ok=True)

        try:
            # Unpack the snapshot archive
            shutil.unpack_archive(str(snapshot_path), str(temp_folder))

            # Check if the main "world" folder exists in the snapshot
            main_world_folder = temp_folder / "world"
            if not main_world_folder.exists():
                embed = discord.Embed(description=':x: The main world folder is missing from the snapshot.\
                                      Aborting restore.',
                                      color=discord.Color.red())
                await waitembed.edit(embed=embed)
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

            # Update embed if any folders were skipped
            if skipped_folders:
                skipped_folders_text = "\n".join([f':warning: Skipping folder "{folder}"\
                                                  as it was not found in the snapshot.' for folder in skipped_folders])
                embed.description += skipped_folders_text
                await waitembed.edit(embed=embed)

            shutil.rmtree(temp_folder, ignore_errors=True)

            # Update the embed with success message
            embed.description += f'\n:white_check_mark: Snapshot "{fancy_name}" has been successfully restored.'
            embed.color = discord.Color.green()
            await waitembed.edit(embed=embed)

        except Exception as e:
            # Catch all exceptions and report them in Discord
            embed = discord.Embed(
                description=f':x: Failed to restore snapshot: {str(e)}',
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            shutil.rmtree(temp_folder, ignore_errors=True)
    else:
        embed = discord.Embed(
            description=f':x: Snapshot restoration process aborted for "{fancy_name}".',
            color=discord.Color.red()
        )
        await confirm_message.edit(embed=embed)
        await confirm_message.clear_reactions()


async def download_snapshot(ctx, snapshot_name):
    c.execute("SELECT path FROM snapshots WHERE fancy_name=?", (snapshot_name,))
    snapshot = c.fetchone()

    if not snapshot:
        embed = discord.Embed(
            description=f':x: Snapshot with the name "{snapshot_name}" not found.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    snapshot_path = Path(snapshot[0])

    if not snapshot_path.exists():
        embed = discord.Embed(
            description=f':x: Snapshot file for "{snapshot_name}" not found.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    initial_message = await ctx.send(
        embed=discord.Embed(
            description=f':hourglass: Starting upload for snapshot "{snapshot_name}"...',
            color=discord.Color.blue()
        )
    )

    try:
        file = discord.File(str(snapshot_path), filename=snapshot_path.name)
        await ctx.send(file=file)

        success_embed = discord.Embed(
            description=f':white_check_mark: Snapshot "{snapshot_name}" has been successfully uploaded.',
            color=discord.Color.green()
        )
        await initial_message.delete()
        await ctx.send(embed=success_embed)
    except Exception as e:
        error_embed = discord.Embed(
            description=f':x: Failed to upload snapshot "{snapshot_name}": {str(e)}',
            color=discord.Color.red()
        )
        await initial_message.edit(embed=error_embed)