"""Jerome 7 Discord Bot — community layer for YU Show Up."""

import os
from datetime import datetime, timedelta, date

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
    nudge_check.start()


# --- /pledge ---

@bot.tree.command(name="pledge", description="Join Jerome7. Start your chain.")
@app_commands.choices(level=[
    app_commands.Choice(name="Beginner", value="beginner"),
    app_commands.Choice(name="Returning", value="returning"),
    app_commands.Choice(name="Active", value="active"),
])
async def pledge_cmd(interaction: discord.Interaction,
                     level: app_commands.Choice[str] = None):
    await interaction.response.defer()
    try:
        _resolve_user(interaction)
        await interaction.followup.send(
            f"**You're in, {interaction.user.display_name}.**\n"
            f"Type `/seven7` — your first session is waiting.\n\n"
            f"*YU SHOW UP — the chain starts now.*"
        )
    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)


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
        timer_url = f"https://jerome7.com/timer"
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

        log_msg = await interaction.followup.send(msg, wait=True)

        # Ask for quick feedback via reactions
        feedback_emojis = ["💪", "👍", "🔥"]  # easy=1, good=3, hard=5
        for emoji in feedback_emojis:
            await log_msg.add_reaction(emoji)

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


# --- /pod ---

@bot.tree.command(name="pod", description="Find your accountability crew. 3-5 builders.")
async def pod_cmd(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        user_id = _resolve_user(interaction)

        # Check for existing pod
        resp = requests.get(f"{API_URL}/pod/{user_id}")
        if resp.ok:
            pod = resp.json()
            members = ", ".join(m["name"] for m in pod["members"])
            msg = (
                f"**{pod['pod_name']}**\n\n"
                f"Members: {members}\n"
            )
            # Show each member's streak
            for m in pod["members"]:
                msg += f"  `{m['current_streak']}d` {m['name']}\n"
            msg += f"\n*Your crew. Show up together.*"
            await interaction.followup.send(msg)
            return

        # Try to match
        resp = requests.post(f"{API_URL}/pod/{user_id}/match")
        if resp.ok:
            data = resp.json()
            if "pod_name" in data:
                members = ", ".join(m["name"] for m in data["members"])
                msg = (
                    f"**{data['pod_name']}** — you're matched.\n\n"
                    f"Members: {members}\n\n"
                    f"*Your crew. The chain is stronger together.*"
                )
            else:
                msg = data.get("message", "No matches yet — more builders coming.")
        else:
            msg = "No matches yet — we'll pair you when more builders join."

        await interaction.followup.send(msg)
    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)


# --- /save ---

@bot.tree.command(name="save", description="Use a streak save. 1 per 30 days.")
async def save_cmd(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        user_id = _resolve_user(interaction)
        resp = requests.post(f"{API_URL}/streak/{user_id}/save")
        if resp.ok and resp.json().get("saved"):
            await interaction.followup.send(
                "**Save used.** Your chain holds for today.\n"
                "*Life happens. The chain understands.*"
            )
        else:
            await interaction.followup.send(
                "No saves available. You get 1 every 30 days.",
                ephemeral=True,
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


# --- Nudge loop — DMs users who are about to skip ---

@tasks.loop(hours=4)
async def nudge_check():
    """Check all known users — DM those at risk of breaking their streak."""
    try:
        resp = requests.get(f"{API_URL}/nudge/at-risk")
        if not resp.ok:
            return
        at_risk = resp.json().get("users", [])

        for user_data in at_risk:
            discord_id = user_data.get("discord_id")
            if not discord_id:
                continue
            try:
                member = await bot.fetch_user(int(discord_id))
                if member:
                    streak = user_data.get("current_streak", 0)
                    nudge_text = user_data.get("nudge", {})
                    subject = nudge_text.get("subject", f"Day {streak + 1} is waiting")
                    body = nudge_text.get("body", "Your Seven 7 is ready. 7 minutes.")
                    cta = nudge_text.get("cta", "Type `/seven7` in the server.")

                    msg = f"**{subject}**\n\n{body}\n\n👉 {cta}"
                    await member.send(msg)
            except Exception:
                continue  # Can't DM this user, skip
    except Exception as e:
        print(f"[Nudge] Error: {e}")


@nudge_check.before_loop
async def before_nudge():
    await bot.wait_until_ready()


# --- Feedback reaction handler ---

FEEDBACK_EMOJI_MAP = {"💪": 1, "👍": 3, "🔥": 5}  # maps to difficulty_rating


@bot.event
async def on_reaction_add(reaction, user):
    """Capture difficulty feedback from /log reaction emojis."""
    if user.bot:
        return
    emoji = str(reaction.emoji)
    if emoji not in FEEDBACK_EMOJI_MAP:
        return

    # Only respond to reactions on messages from the bot
    if reaction.message.author != bot.user:
        return

    # Check that the message looks like a /log response (has "Logged" in it)
    if "Logged" not in (reaction.message.content or ""):
        return

    difficulty = FEEDBACK_EMOJI_MAP[emoji]
    try:
        # Resolve user to get their internal user_id
        resp = requests.post(f"{API_URL}/pledge", json={
            "name": user.display_name,
            "discord_id": str(user.id),
        })
        resp.raise_for_status()
        user_id = resp.json()["user_id"]

        # Store the feedback
        requests.post(f"{API_URL}/log/{user_id}/feedback", json={
            "difficulty": difficulty,
        })
    except Exception as e:
        print(f"[Feedback] Error storing reaction feedback: {e}")


def run():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("[Jerome 7] DISCORD_TOKEN not set.")
        return
    bot.run(token)


if __name__ == "__main__":
    run()
