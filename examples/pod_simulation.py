"""Demo: simulate pod formation with sample users."""

from src.db.database import init_db, SessionLocal
from src.db.models import User, FitnessLevel
from src.agents.community import CommunityMatcherAgent
from src.agents.context import build_user_context


def main():
    init_db()
    db = SessionLocal()

    # Create 5 test users
    users = []
    for i, (name, tz, level) in enumerate([
        ("Alex", "America/New_York", FitnessLevel.beginner),
        ("Jordan", "America/New_York", FitnessLevel.beginner),
        ("Sam", "America/Chicago", FitnessLevel.returning),
        ("Casey", "America/New_York", FitnessLevel.returning),
        ("Riley", "Europe/London", FitnessLevel.active),
    ]):
        user = User(name=name, timezone=tz, fitness_level=level)
        db.add(user)
        db.flush()
        users.append(user)

    db.commit()

    # Try to form a pod for the first user
    matcher = CommunityMatcherAgent()
    ctx = build_user_context(users[0].id, db)
    match = matcher.find_pod(ctx, db)

    if match:
        print(f"\n  Pod match found! Score: {match.compatibility_score:.2f}")
        print(f"  Members: {len(match.proposed_members)} people")

        pod = matcher.form_pod(match.proposed_members, db)
        print(f"  Pod name: {pod.name}\n")
    else:
        print("\n  No pod match found yet.\n")

    db.close()


if __name__ == "__main__":
    main()
