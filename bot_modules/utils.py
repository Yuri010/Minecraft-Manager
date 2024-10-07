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
import time

# Third-party imports
import discord
import requests


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
        print(f"Failed to retrieve public IP: {str(e)}")
        return None


async def ping(ctx):
    start_time = time.time()
    message = await ctx.send('Pinging...')
    end_time = time.time()

    latency = (end_time - start_time) * 1000

    embed = discord.Embed(description=f'Pong! Latency: {latency:.2f} ms', color=discord.Color.green())
    await message.edit(content='', embed=embed)