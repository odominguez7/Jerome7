"""Jerome 7 CLI — yu seven7 / yu log / yu streak / yu pod."""

import json
import os
import sys
from pathlib import Path

import click
import requests

CONFIG_DIR = Path.home() / ".jerome7"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_API_URL = "http://localhost:8000"


def get_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config):
    CONFIG_DIR.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def get_api_url():
    config = get_config()
    return config.get("api_url", DEFAULT_API_URL)


def get_user_id():
    config = get_config()
    uid = config.get("user_id")
    if not uid:
        click.echo("Not pledged yet. Run: jerome7 pledge")
        sys.exit(1)
    return uid


@click.group()
def cli():
    """Jerome 7 — YU Show Up. 7 minutes a day."""
    pass


@cli.command()
def pledge():
    """Take the pledge. Start your chain."""
    click.echo("\n  JEROME 7 — YU SHOW UP")
    click.echo("  7 minutes a day. An act of love.\n")

    name = click.prompt("  Your name")
    timezone = click.prompt("  Your timezone", default="UTC")
    level = click.prompt(
        "  Fitness level",
        type=click.Choice(["beginner", "returning", "active"]),
        default="beginner",
    )

    api_url = get_api_url()
    try:
        resp = requests.post(f"{api_url}/pledge", json={
            "name": name,
            "timezone": timezone,
            "fitness_level": level,
        })
        resp.raise_for_status()
        data = resp.json()

        config = get_config()
        config["user_id"] = data["user_id"]
        config["name"] = data["name"]
        config["api_url"] = api_url
        save_config(config)

        click.echo(f"\n  You're in, {name}.")
        click.echo("  Your Seven 7 will be ready tomorrow morning.")
        click.echo("  Run `jerome7 seven7` to see it.\n")

    except requests.ConnectionError:
        click.echo("\n  Could not connect to the API.")
        click.echo(f"  Make sure the server is running at {api_url}")
        click.echo("  Run: make dev\n")
    except Exception as e:
        click.echo(f"\n  Error: {e}\n")


@cli.command()
def seven7():
    """Get today's personalized Seven 7 session."""
    user_id = get_user_id()
    api_url = get_api_url()

    try:
        resp = requests.get(f"{api_url}/seven7/{user_id}")
        resp.raise_for_status()
        data = resp.json()

        click.echo(f"\n  {data.get('greeting', '')}\n")
        click.echo(f"  ── {data.get('session_title', 'The Seven 7')} ──\n")

        for block in data.get("blocks", []):
            mins = block["duration_seconds"] // 60
            secs = block["duration_seconds"] % 60
            time_str = f"{mins}:{secs:02d}" if mins else f":{secs:02d}"
            click.echo(f"  [{time_str}]  {block['name']}")
            click.echo(f"          {block['instruction']}")
            click.echo(f"          ↳ {block['why_today']}\n")

        click.echo(f"  {data.get('closing', '')}")
        click.echo(f"  Total: {data.get('total_seconds', 420) // 60} minutes\n")

    except requests.ConnectionError:
        click.echo("\n  Could not connect. Is the server running? (make dev)\n")
    except Exception as e:
        click.echo(f"\n  Error: {e}\n")


@cli.command()
@click.option("--note", "-n", default=None, help="Add a note to your log")
def log(note):
    """Log your Seven 7 session. Build the chain."""
    user_id = get_user_id()
    api_url = get_api_url()

    try:
        resp = requests.post(f"{api_url}/log/{user_id}", json={
            "duration_minutes": 7,
            "note": note,
        })
        resp.raise_for_status()
        data = resp.json()

        streak = data.get("new_streak", 0)
        chain = "◉ " * min(streak, 30)
        if streak > 30:
            chain = f"... {chain}"

        click.echo(f"\n  Logged. Day {streak}.")
        click.echo(f"\n  {chain}\n")

        milestone = data.get("milestone_reached")
        if milestone:
            click.echo(f"  🔥 MILESTONE: {milestone} days unbroken. The chain holds.\n")

    except requests.ConnectionError:
        click.echo("\n  Could not connect. Is the server running? (make dev)\n")
    except Exception as e:
        click.echo(f"\n  Error: {e}\n")


@cli.command()
def streak():
    """Show your streak chain."""
    user_id = get_user_id()
    api_url = get_api_url()

    try:
        resp = requests.get(f"{api_url}/streak/{user_id}")
        resp.raise_for_status()
        data = resp.json()

        click.echo(f"\n  {data.get('username', 'You')} — {data['current_streak']} days unbroken\n")

        chain_data = data.get("chain", [])
        chain_str = " ".join("◉" if d == "filled" else "○" for d in chain_data[-30:])
        click.echo(f"  {chain_str}\n")

        click.echo(f"  Current:  {data['current_streak']} days")
        click.echo(f"  Longest:  {data['longest_streak']} days")
        click.echo(f"  Total:    {data['total_sessions']} sessions")
        click.echo(f"  Next:     {data.get('next_milestone', '?')} days")
        click.echo(f"  Saves:    {data.get('saves_remaining', 1)} remaining\n")

    except requests.ConnectionError:
        click.echo("\n  Could not connect. Is the server running? (make dev)\n")
    except Exception as e:
        click.echo(f"\n  Error: {e}\n")


@cli.command()
def pod():
    """Show your pod."""
    user_id = get_user_id()
    api_url = get_api_url()

    try:
        resp = requests.get(f"{api_url}/pod/{user_id}")
        if resp.status_code == 404:
            click.echo("\n  No pod yet. You'll be matched within 24 hours.\n")
            return
        resp.raise_for_status()
        data = resp.json()

        click.echo(f"\n  Pod: {data['pod_name']}\n")
        for member in data.get("members", []):
            click.echo(f"    {member['name']} — {member['current_streak']} days")
        click.echo()

    except requests.ConnectionError:
        click.echo("\n  Could not connect. Is the server running? (make dev)\n")
    except Exception as e:
        click.echo(f"\n  Error: {e}\n")


@cli.command()
@click.option("--energy", "-e", type=click.Choice(["low", "medium", "high"]), required=True)
def checkin(energy):
    """Set your energy level. Regenerates today's Seven 7."""
    user_id = get_user_id()
    api_url = get_api_url()

    try:
        resp = requests.post(f"{api_url}/seven7/{user_id}/checkin", json={"energy": energy})
        resp.raise_for_status()
        data = resp.json()

        click.echo(f"\n  Energy set to {energy}. Your Seven 7 has been regenerated.\n")
        click.echo(f"  ── {data.get('session_title', '')} ──\n")

        for block in data.get("blocks", []):
            mins = block["duration_seconds"] // 60
            secs = block["duration_seconds"] % 60
            time_str = f"{mins}:{secs:02d}" if mins else f":{secs:02d}"
            click.echo(f"  [{time_str}]  {block['name']}")
            click.echo(f"          {block['instruction']}\n")

    except requests.ConnectionError:
        click.echo("\n  Could not connect. Is the server running? (make dev)\n")
    except Exception as e:
        click.echo(f"\n  Error: {e}\n")


if __name__ == "__main__":
    cli()
