import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import json
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

# קובץ שמירת ה-vouches והערוצים המורשים
VOUCHES_FILE = "vouches.json"
CHANNELS_FILE = "allowed_channels.json"

def load_vouches():
    if os.path.exists(VOUCHES_FILE):
        with open(VOUCHES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_vouches(data):
    with open(VOUCHES_FILE, "w") as f:
        json.dump(data, f)

def load_allowed_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_allowed_channels(data):
    with open(CHANNELS_FILE, "w") as f:
        json.dump(data, f)

user_vouches = load_vouches()
allowed_channels = load_allowed_channels()

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot is ready as {bot.user} (ID: {bot.user.id})")

@bot.tree.command(name="vouch", description="Give a vouch to a member")
@app_commands.describe(member="User to vouch for", stars="Rating 1-5", details="Details")
async def vouch(interaction: discord.Interaction, member: discord.Member, stars: int, details: str):
    guild_id = str(interaction.guild.id)
    channel_id = interaction.channel.id
    if guild_id in allowed_channels and channel_id not in allowed_channels[guild_id]:
        await interaction.response.send_message("❌ This channel is not allowed for bot commands.", ephemeral=True)
        return

    if stars < 1 or stars > 5:
        await interaction.response.send_message("Please provide stars between 1 and 5.", ephemeral=True)
        return

    if str(member.id) in user_vouches:
        user_vouches[str(member.id)] += 1
    else:
        user_vouches[str(member.id)] = 1
    save_vouches(user_vouches)

    await interaction.response.send_message(f"The vouch has been added to {member.mention}!")

    embed = discord.Embed(
        title=f"👍 New Vouch created for {member.display_name}",
        color=discord.Color.dark_gray()
    )
    embed.add_field(name="⭐ Rating", value=f"{'🌟' * stars} ({stars}/5)", inline=False)
    embed.add_field(name="📝 Vouch", value=details, inline=False)
    embed.add_field(name="👤 Vouched by", value=interaction.user.mention, inline=True)
    embed.add_field(name="📅 Vouched at", value=datetime.utcnow().strftime("%m/%d/%Y, %I:%M:%S %p UTC"), inline=True)
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    embed.set_footer(text="⚠️ Use a reputable middleman for safe transactions.")
    await interaction.channel.send(embed=embed)

@bot.tree.command(name="vouches", description="Check how many vouches a user has")
@app_commands.describe(member="User to check")
async def vouches(interaction: discord.Interaction, member: discord.Member):
    count = user_vouches.get(str(member.id), 0)
    await interaction.response.send_message(f"{member.display_name} has {count} vouches.")

@bot.tree.command(name="delete_vouches", description="Remove vouches from a user")
@app_commands.describe(member="User to remove vouches from", amount="Amount to remove")
async def delete_vouches(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Only admins can use this command.", ephemeral=True)
        return

    current = user_vouches.get(str(member.id), 0)
    user_vouches[str(member.id)] = max(current - amount, 0)
    save_vouches(user_vouches)
    await interaction.response.send_message(f"Removed {amount} vouches from {member.display_name}. Now they have {user_vouches[str(member.id)]}.")

@bot.tree.command(name="add_vouches", description="Add vouches to a user")
@app_commands.describe(member="User to add vouches to", amount="Amount to add")
async def add_vouches(interaction: discord.Interaction, member: discord.Member, amount: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Only admins can use this command.", ephemeral=True)
        return

    user_vouches[str(member.id)] = user_vouches.get(str(member.id), 0) + amount
    save_vouches(user_vouches)
    await interaction.response.send_message(f"Added {amount} vouches to {member.display_name}. Total: {user_vouches[str(member.id)]}.")

@bot.tree.command(name="top_vouched", description="Show top 10 users with most vouches")
async def top_vouched(interaction: discord.Interaction):
    sorted_vouches = sorted(user_vouches.items(), key=lambda x: x[1], reverse=True)[:10]
    description = "\n".join([f"{i+1}. <@{uid}> — {count} vouches" for i, (uid, count) in enumerate(sorted_vouches)])
    embed = discord.Embed(title="🏆 Top 10 Vouched Users", description=description or "No data.", color=discord.Color.dark_gray())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="set_channel", description="Set allowed channel for bot commands")
@app_commands.describe(channel="Choose the channel")
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Only admins can use this command.", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    allowed_channels.setdefault(guild_id, [])
    if channel.id not in allowed_channels[guild_id]:
        allowed_channels[guild_id].append(channel.id)
        save_allowed_channels(allowed_channels)
        await interaction.response.send_message(f"Allowed channel set to: {channel.mention}", ephemeral=True)
    else:
        await interaction.response.send_message("Channel already allowed.", ephemeral=True)

@bot.tree.command(name="remove_set_channel", description="Remove an allowed channel (admin only)")
@app_commands.describe(channel="Choose the channel to remove")
async def remove_set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Only admins can use this command.", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    if guild_id in allowed_channels and channel.id in allowed_channels[guild_id]:
        allowed_channels[guild_id].remove(channel.id)
        if not allowed_channels[guild_id]:
            del allowed_channels[guild_id]
        save_allowed_channels(allowed_channels)
        await interaction.response.send_message(f"{channel.mention} has been removed from allowed channels.", ephemeral=True)
    else:
        await interaction.response.send_message("This channel is not in the allowed list.", ephemeral=True)

bot.run(os.getenv("DISCORD_TOKEN"))
