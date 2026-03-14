"""Jerome 7 Discord Bot — community layer for YU Show Up."""

import os
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks
import requests

API_URL = os.getenv("YU_API_URL", "http://localhost:8000")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


def _get_or_create_user(interaction: discord.Interaction, name: str = None,
                        timezone: str = "UTC", level: str = "beginner") -> str | None:
    """Pledge (or re-pledge) and return internal user_id."""
    resp = requests.post(f"{API_URL}/pledge", json={
        "name": name or interaction.user.display_name,
        "discord_id": str(interaction.user.id),
        "timezone": timezone,
        "fitness_level": level,
    })
    resp.raise_for_status()
    return resp.json()["user_id"]


@bot.event
async def on_ready():
    print(f"[Jerome 7] Bot ready as {bot.user}")
    if GUILD_ID:
        guild = discord.Object(id=int(GUILD_ID))
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    else:
        await bot.tree.sync()
    daily_message.start()


# --- Slash commands ---

@bot.tree.command(name="pledge", description="Take the pledge. Start your chain.")
@app_commands.describe(timezone="Your timezone (e.g. America/New_York)", level="Fitness level")
@app_commands.choices(level=[
    app_commands.Choice(name="Beginner", value="beginner"),
    app_commands.Choice(name="Returning", value="returning"),
    app_commands.Choice(name="Active", value="active"),
])
async def pledge_cmd(interaction: discord.Interaction, timezone: str = "UTC",
                     level: app_commands.Choice[str] = None):
    fitness = level.value if level else "beginner"
    try:
        _get_or_create_user(interaction, timezone=timezone, level=fitness)
        embed = discord.Embed(
            title="You're in.",
            description=f"Welcome, {interaction.user.display_name}. Your Seven 7 is waiting.\n"
                        f"Run `/seven7` to see today's session.",
            color=0xE85D04,
        )
        embed.set_footer(text="YU SHOW UP — The chain starts now.")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"Error: {e}", ephemeral=True)


@bot.tree.command(name="seven7", description="Get today's personalized Seven 7 session.")
async def seven7_cmd(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        user_id = _get_or_create_user(interaction)
        resp = requests.get(f"{API_URL}/seven7/{user_id}")
        resp.raise_for_status()
        data = resp.json()

        embed = discord.Embed(
            title=f"── {data.get('session_title', 'The Seven 7')} ──",
            description=data.get("greeting", ""),
            color=0xE85D04,
        )
        for block in data.get("blocks", []):
            mins = block["duration_seconds"] // 60
            secs = block["duration_seconds"] % 60
            embed.add_field(
                name=f"[{mins}:{secs:02d}] {block['name']}",
                value=f"{block['instruction']}\n*{block['why_today']}*",
                inline=False,
            )
        embed.set_footer(text=data.get("closing", "YU SHOW UP"))
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)


@bot.tree.command(name="log", description="Log your Seven 7 session.")
@app_commands.describe(note="Optional note about today's session")
async def log_cmd(interaction: discord.Interaction, note: str = None):
    await interaction.response.defer()
    try:
        user_id = _get_or_create_user(interaction)
        resp = requests.post(f"{API_URL}/log/{user_id}", json={
            "duration_minutes": 7, "note": note,
        })
        resp.raise_for_status()
        data = resp.json()

        streak = data.get("new_streak", 0)
        chain = "◉ " * min(streak, 20)

        embed = discord.Embed(
            title=f"Day {streak}. Logged.",
            description=chain,
            color=0xE85D04,
        )

        milestone = data.get("milestone_reached")
        if milestone:
            embed.add_field(
                name="MILESTONE",
                value=f"{milestone} days unbroken. The chain holds.",
                inline=False,
            )

        embed.set_footer(text="YU SHOW UP")
        await interaction.followup.send(embed=embed)

        if milestone and interaction.guild:
            for channel in interaction.guild.text_channels:
                if channel.name == "milestones":
                    await channel.send(
                        f"<@{interaction.user.id}> just hit **{milestone} days** unbroken. The chain holds."
                    )
                    break

    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)


@bot.tree.command(name="streak", description="Show your streak chain.")
async def streak_cmd(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        user_id = _get_or_create_user(interaction)
        resp = requests.get(f"{API_URL}/streak/{user_id}")
        resp.raise_for_status()
        data = resp.json()

        chain_data = data.get("chain", [])
        chain = " ".join("◉" if d == "filled" else "○" for d in chain_data[-30:])

        embed = discord.Embed(
            title=f"{data.get('username', interaction.user.display_name)} — {data['current_streak']} days unbroken",
            description=chain or "No sessions yet. Run /seven7 to start.",
            color=0xE85D04,
        )
        embed.add_field(name="Current", value=str(data["current_streak"]), inline=True)
        embed.add_field(name="Longest", value=str(data["longest_streak"]), inline=True)
        embed.add_field(name="Total", value=str(data["total_sessions"]), inline=True)
        embed.add_field(name="Next milestone", value=str(data.get("next_milestone", 7)), inline=True)
        embed.set_footer(text="YU SHOW UP")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)


@bot.tree.command(name="checkin", description="Set your energy level and regenerate today's session.")
@app_commands.choices(energy=[
    app_commands.Choice(name="Low", value="low"),
    app_commands.Choice(name="Medium", value="medium"),
    app_commands.Choice(name="High", value="high"),
])
async def checkin_cmd(interaction: discord.Interaction, energy: app_commands.Choice[str]):
    await interaction.response.defer()
    try:
        user_id = _get_or_create_user(interaction)
        resp = requests.post(f"{API_URL}/seven7/{user_id}/checkin", json={"energy": energy.value})
        resp.raise_for_status()
        data = resp.json()
        embed = discord.Embed(
            title=f"Energy: {energy.value}. Seven 7 regenerated.",
            description=f"── {data.get('session_title', '')} ──",
            color=0xE85D04,
        )
        embed.set_footer(text="YU SHOW UP")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)


# --- Automated daily message ---

@tasks.loop(hours=24)
async def daily_message():
    """Post daily to #show-up-daily."""
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name == "show-up-daily":
                await channel.send(
                    "**Seven 7 time.**\n"
                    "Today is yours. 7 minutes. Show up.\n\n"
                    "*YU SHOW UP*"
                )
                break


def run():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("[Jerome 7] DISCORD_TOKEN not set. Bot not starting.")
        return
    bot.run(token)


if __name__ == "__main__":
    run()
