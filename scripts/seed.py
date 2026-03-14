"""Seed the database with 3 sample users and streaks for development."""

from datetime import datetime, date, timedelta

from src.db.database import init_db, SessionLocal
from src.db.models import User, Streak, FitnessLevel


def seed():
    init_db()
    db = SessionLocal()

    users_data = [
        {
            "id": "user-omar-001",
            "name": "Omar",
            "email": "omar@example.com",
            "timezone": "America/New_York",
            "fitness_level": FitnessLevel.active,
            "streak": {"current_streak": 47, "longest_streak": 47, "total_sessions": 47,
                       "last_session_date": date.today() - timedelta(days=1)},
        },
        {
            "id": "user-kai-002",
            "name": "Kai",
            "email": "kai@example.com",
            "timezone": "America/Los_Angeles",
            "fitness_level": FitnessLevel.returning,
            "streak": {"current_streak": 12, "longest_streak": 23, "total_sessions": 35,
                       "last_session_date": date.today()},
        },
        {
            "id": "user-nova-003",
            "name": "Nova",
            "email": "nova@example.com",
            "timezone": "Europe/London",
            "fitness_level": FitnessLevel.beginner,
            "streak": {"current_streak": 3, "longest_streak": 3, "total_sessions": 3,
                       "last_session_date": date.today() - timedelta(days=2)},
        },
    ]

    for data in users_data:
        streak_data = data.pop("streak")
        existing = db.query(User).filter(User.id == data["id"]).first()
        if existing:
            print(f"  Skipping {data['name']} (already exists)")
            continue

        user = User(**data)
        db.add(user)
        db.flush()

        streak = Streak(user_id=user.id, **streak_data)
        db.add(streak)
        print(f"  Created {data['name']} — streak: {streak_data['current_streak']} days")

    db.commit()
    db.close()
    print("\nSeed complete.")


if __name__ == "__main__":
    seed()
