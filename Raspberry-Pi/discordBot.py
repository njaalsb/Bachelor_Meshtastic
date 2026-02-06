import meshtastic.serial_interface
from pubsub import pub
import discord
import asyncio

DISCORD_TOKEN = "MTQ2ODI0Nzg0MDEzNTQ1MDc4OA.GdvdE1.Hovxx4XZD0UH9BUh-WZGwHUQLgjvkjQrD7bB38"
CHANNEL_ID = 1468248951076683847

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print("Discord-bot klar")

async def send_to_discord(text):
    channel = client.get_channel(CHANNEL_ID)
    await channel.send(text)

def on_receive(packet, interface):
    if 'decoded' in packet and 'text' in packet['decoded']:
        msg = packet['decoded']['text']
        asyncio.run_coroutine_threadsafe(
            send_to_discord(msg),
            client.loop
        )

iface = meshtastic.serial_interface.SerialInterface()
pub.subscribe(on_receive, "meshtastic.receive")

client.run(DISCORD_TOKEN)
