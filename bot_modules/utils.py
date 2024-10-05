# version 1.3.0
# This file houses miscellaneous utilities
import discord
import requests
import time


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


async def ping(ctx):
    start_time = time.time()
    message = await ctx.send('Pinging...')
    end_time = time.time()

    latency = (end_time - start_time) * 1000

    embed = discord.Embed(description=f'Pong! Latency: {latency:.2f} ms', color=discord.Color.green())
    await message.edit(content='', embed=embed)