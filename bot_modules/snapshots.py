# version 1.3.0
import discord
import os
import time
import shutil
import sqlite3
import asyncio

conn = sqlite3.connect('minecraft_manager.db')
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


async def create_snapshot(ctx, bot, server_running, suppress_success_message=False):
    if server_running:
        embed = discord.Embed(description=':x: Cannot create a snapshot while the server is running.',
                              color=discord.Color.red())
        await ctx.send(embed=embed)
        return

    temp_folder = "temp_snapshot"
    os.makedirs(temp_folder, exist_ok=True)

    try:
        script_path = os.path.dirname(os.path.abspath(__file__))
        snapshots_folder = os.path.join(script_path, "snapshots")

        world_folders = ["world", "world_nether", "world_the_end"]
        for folder in world_folders:
            shutil.copytree(os.path.join(script_path, "..", folder), os.path.join(temp_folder, folder))

        nameask = discord.Embed(
            description='📝 Please provide a name for this snapshot.',
            color=discord.Color.blue()
        )
        namemsg = await ctx.send(embed=nameask)

        def check_author(m):
            return m.author == ctx.author and m.channel == ctx.channel

        try:
            name_reply = await bot.wait_for('message', check=check_author, timeout=120)
            snapshot_name = name_reply.content
        except asyncio.TimeoutError:
            snapshot_name = f"Snapshot {int(time.time())}"

        descask = discord.Embed(
            description='📝 Please provide a description for this snapshot.',
            color=discord.Color.blue()
        )
        descmsg = await ctx.send(embed=descask)

        try:
            desc_reply = await bot.wait_for('message', check=check_author, timeout=120)
            snapshot_description = desc_reply.content
        except asyncio.TimeoutError:
            snapshot_description = ""

        waitembed = discord.Embed(
            description=f':rocket: Creating snapshot {snapshot_name}...',
            color=discord.Color.blue()
        )
        waitmsg = await ctx.send(embed=waitembed)

        snapshot_filename = f"snapshot_{int(time.time())}"
        snapshot_path = os.path.join(snapshots_folder, snapshot_filename)

        shutil.make_archive(snapshot_path, 'zip', temp_folder)

        file_size = os.path.getsize(f"{snapshot_path}.zip")

        current_date = time.strftime('%Y-%m-%d %H:%M:%S')
        c.execute("INSERT INTO snapshots(filename, fancy_name, path, file_size, date, notes) VALUES (?, ?, ?, ?, ?, ?)",
                  (f"{snapshot_filename}.zip", snapshot_name, f"{snapshot_path}.zip", file_size, current_date,
                   snapshot_description))
        conn.commit()

        if not suppress_success_message:
            success_embed = discord.Embed(
                description=f':white_check_mark: Snapshot "{snapshot_name}" created successfully.',
                color=discord.Color.green()
            )
            await waitmsg.edit(embed=success_embed)

    except Exception as e:
        error_embed = discord.Embed(
            description=f':x: Failed to create snapshot "{snapshot_name}": {str(e)}',
            color=discord.Color.red()
        )
        await ctx.send(embed=error_embed)

    finally:
        shutil.rmtree(temp_folder, ignore_errors=True)
        await namemsg.delete()
        await descmsg.delete()
        await name_reply.delete()
        await desc_reply.delete()
        if suppress_success_message:
            await waitmsg.delete()


async def list_snapshots(ctx):
    c.execute("SELECT * FROM snapshots")
    snapshots = c.fetchall()

    normal_embed = discord.Embed(color=discord.Color.green())
    excluded_entries = []

    for snapshot in snapshots:
        file_path = snapshot[3]

        if not os.path.exists(file_path):
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

    snapshot_id, filename, fancy_name, path, file_size, date, notes = snapshot

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
        os.remove(path)
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

    c.execute("SELECT * FROM snapshots WHERE fancy_name=?", (snapshot_name,))
    snapshot = c.fetchone()

    if not snapshot:
        embed = discord.Embed(
            description=f':x: Snapshot with the name "{snapshot_name}" not found.',
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    snapshot_id, filename, fancy_name, path, file_size, date, notes = snapshot

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
        await create_snapshot(ctx, suppress_success_message=True)
        await confirm_message.delete()

        world_folders = ["world", "world_nether", "world_the_end"]
        script_path = os.path.dirname(os.path.abspath(__file__))

        for folder in world_folders:
            shutil.rmtree(os.path.join(script_path, "..", folder), ignore_errors=True)

        temp_folder = "temp_restore"
        os.makedirs(temp_folder, exist_ok=True)

        try:
            shutil.unpack_archive(path, temp_folder)

            for folder in world_folders:
                shutil.move(os.path.join(temp_folder, folder), os.path.join(script_path, ".."))

            shutil.rmtree(temp_folder, ignore_errors=True)

            embed = discord.Embed(
                description=f':white_check_mark: Snapshot "{fancy_name}" has been successfully restored.',
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except Exception as e:
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

    snapshot_path = snapshot[0]

    if not os.path.exists(snapshot_path):
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
        file = discord.File(snapshot_path, filename=os.path.basename(snapshot_path))
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
        await initial_message.clear_reactions()