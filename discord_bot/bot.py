"""Jerome 7 Discord Bot — community layer for YU Show Up."""

import os

import discord
from discord import app_commands
from discord.ext import commands, tasks
import requests

API_URL = os.getenv("YU_API_URL", "http://localhost:8000")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

PHASE_EMOJI = {"prime": "🌅", "build": "🔨", "move": "⚡", "reset": "🫁"}


def _resolve_user(interaction: discord.Interaction) -> str | None:
    """Pledge or look up user, return internal user_id."""
    resp = requests.post(f"{API_URL}/pledge", json={
        "name": interaction.user.display_name,
        "discord_id": str(interaction.user.id),
    })
    resp.raise_for_status()
    return resp.json()["user_id"]


def _format_session(data: dict) -> str:
    """Format a session as a clean, minimal text block."""
    title = data.get("session_title", "the seven 7")
    lines = [f"**{title}**", ""]
    for b in data.get("blocks", []):
        emoji = PHASE_EMOJI.get(b.get("phase", ""), "▸")
        lines.append(f"{emoji} `{b['duration_seconds']}s` **{b['name']}** — {b['instruction']}")
    lines.append("")
    lines.append(f"*{data.get('closing', 'yu showed up.')}*")
    return "\n".join(lines)


def _streak_grid(chain: list[str], streak: int) -> str:
    """Wordle-style 7-day grid + streak count."""
    last7 = chain[-7:] if chain else []
    while len(last7) < 7:
        last7.insert(0, "empty")
    grid = " ".join("🟧" if d == "filled" else "⬛" for d in last7)
    return f"{grid}  `{streak}d`"


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


# --- /pledge ---

@bot.tree.command(name="pledge", description="Join Jerome7. Start your chain.")
@app_commands.choices(level=[
    app_commands.Choice(name="Beginner", value="beginner"),
    app_commands.Choice(name="Returning", value="returning"),
    app_commands.Choice(name="Active", value="active"),
])
async def pledge_cmd(interaction: discord.Interaction,
                     level: app_commands.Choice[str] = None):
    try:
        _resolve_user(interaction)
        await interaction.response.send_message(
            f"**You're in, {interaction.user.display_name}.**\n"
            f"Type `/seven7` — your first session is waiting.\n\n"
            f"*YU SHOW UP — the chain starts now.*"
        )
    except Exception as e:
        await interaction.response.send_message(f"Error: {e}", ephemeral=True)


# --- /seven7 ---

@bot.tree.command(name="seven7", description="Today's Seven 7. Same session for everyone.")
async def seven7_cmd(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        user_id = _resolve_user(interaction)
        # Get today's universal daily session
        resp = requests.get(f"{API_URL}/daily")
        resp.raise_for_status()
        data = resp.json()

        msg = _format_session(data)
        timer_url = f"{API_URL}/session/{user_id}/timer"
        msg += f"\n\n👉 [**Open timer**]({timer_url}) — follow along in real time"
        msg += f"\n\nWhen you're done: `/log`"

        await interaction.followup.send(msg)
    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)


# --- /log ---

@bot.tree.command(name="log", description="Log today's session. Keep the chain.")
@app_commands.describe(note="How did it feel? (optional)")
async def log_cmd(interaction: discord.Interaction, note: str = None):
    await interaction.response.defer()
    try:
        user_id = _resolve_user(interaction)
        resp = requests.post(f"{API_URL}/log/{user_id}", json={
            "duration_minutes": 7, "note": note,
        })
        resp.raise_for_status()
        data = resp.json()

        streak = data.get("new_streak", 0)

        # Get streak chain for the grid
        streak_resp = requests.get(f"{API_URL}/streak/{user_id}")
        chain = []
        if streak_resp.ok:
            chain = streak_resp.json().get("chain", [])

        grid = _streak_grid(chain, streak)

        share_url = f"{API_URL}/share/{user_id}"
        msg = f"**Day {streak}. Logged.**\n\n{grid}\n\n"

        milestone = data.get("milestone_reached")
        if milestone:
            msg += f"🔥 **{milestone} days unbroken.** The chain holds.\n\n"

        msg += f"[**Share your chain**]({share_url}) · *yu showed up.*"

        await interaction.followup.send(msg)

        # Post milestone to #milestones
        if milestone and interaction.guild:
            for channel in interaction.guild.text_channels:
                if channel.name == "milestones":
                    await channel.send(
                        f"🔥 **{interaction.user.display_name}** hit **{milestone} days**.\n"
                        f"{grid}\n*The chain holds.*"
                    )
                    break

    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)


# --- /streak ---

@bot.tree.command(name="streak", description="See your chain.")
async def streak_cmd(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        user_id = _resolve_user(interaction)
        resp = requests.get(f"{API_URL}/streak/{user_id}")
        resp.raise_for_status()
        data = resp.json()

        chain = data.get("chain", [])
        streak = data["current_streak"]
        grid = _streak_grid(chain, streak)

        msg = f"**{interaction.user.display_name}** — {streak} days\n\n{grid}\n\n"
        msg += f"Longest: `{data['longest_streak']}d` · Total: `{data['total_sessions']}` · Next: `{data.get('next_milestone', 7)}d`"

        await interaction.followup.send(msg)
    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)


# --- /checkin ---

@bot.tree.command(name="checkin", description="Set your energy. Session adapts.")
@app_commands.choices(energy=[
    app_commands.Choice(name="Low 🌙", value="low"),
    app_commands.Choice(name="Medium ☀️", value="medium"),
    app_commands.Choice(name="High ⚡", value="high"),
])
async def checkin_cmd(interaction: discord.Interaction, energy: app_commands.Choice[str]):
    await interaction.response.defer()
    try:
        user_id = _resolve_user(interaction)
        resp = requests.post(f"{API_URL}/seven7/{user_id}/checkin", json={"energy": energy.value})
        resp.raise_for_status()
        await interaction.followup.send(
            f"Energy: **{energy.name}**. Your session adapted.\n"
            f"Type `/seven7` to see it."
        )
    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)


# --- Daily auto-post ---

@tasks.loop(hours=24)
async def daily_message():
    try:
        resp = requests.get(f"{API_URL}/daily")
        if not resp.ok:
            return
        data = resp.json()
        msg = f"☀️ **DAILY SEVEN7**\n\n{_format_session(data)}\n\n"
        msg += "Type `/seven7` to get the timer. `/log` when done."
    except Exception:
        msg = "**Seven 7 time.** 7 minutes. Show up. `/seven7`"

    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name == "show-up-daily":
                await channel.send(msg)
                break


def run():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("[Jerome 7] DISCORD_TOKEN not set.")
        return
    bot.run(token)


if __name__ == "__main__":
    run()
