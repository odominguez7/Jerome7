"""Tests for streak logic — the soul of Jerome7."""

from datetime import date, timedelta
from unittest.mock import MagicMock

from src.agents.streak import StreakAgent
from src.agents.context import MILESTONES
from src.db.models import Streak


def _make_streak(**kwargs):
    defaults = {
        "user_id": "test-user",
        "current_streak": 0,
        "longest_streak": 0,
        "total_sessions": 0,
        "streak_broken_count": 0,
        "saves_used": 0,
        "last_session_date": None,
        "last_save_date": None,
    }
    defaults.update(kwargs)
    s = MagicMock(spec=Streak)
    for k, v in defaults.items():
        setattr(s, k, v)
    return s


def _mock_db(streak=None):
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value.first.return_value = streak
    return db


class TestStreakUpdate:
    def test_first_session(self):
        agent = StreakAgent()
        streak = _make_streak()
        db = _mock_db(streak)
        result = agent.update_streak("test-user", None, db)
        assert result.new == 1
        assert streak.current_streak == 1
        assert streak.total_sessions == 1

    def test_consecutive_day(self):
        agent = StreakAgent()
        streak = _make_streak(
            current_streak=5,
            last_session_date=date.today() - timedelta(days=1),
            total_sessions=5,
        )
        db = _mock_db(streak)
        result = agent.update_streak("test-user", None, db)
        assert result.new == 6
        assert result.previous == 5

    def test_two_day_gap_still_safe(self):
        agent = StreakAgent()
        streak = _make_streak(
            current_streak=10,
            last_session_date=date.today() - timedelta(days=2),
            total_sessions=10,
        )
        db = _mock_db(streak)
        result = agent.update_streak("test-user", None, db)
        assert result.new == 11
        assert result.broken is False

    def test_three_day_gap_breaks_streak(self):
        agent = StreakAgent()
        streak = _make_streak(
            current_streak=10,
            longest_streak=10,
            last_session_date=date.today() - timedelta(days=3),
            total_sessions=10,
        )
        db = _mock_db(streak)
        result = agent.update_streak("test-user", None, db)
        assert result.new == 1
        assert result.broken is True
        assert streak.streak_broken_count == 1

    def test_duplicate_log_same_day(self):
        agent = StreakAgent()
        streak = _make_streak(
            current_streak=5,
            last_session_date=date.today(),
            total_sessions=5,
        )
        db = _mock_db(streak)
        result = agent.update_streak("test-user", None, db)
        assert result.new == 5
        assert result.previous == 5
        assert streak.total_sessions == 5  # no increment

    def test_longest_streak_tracked(self):
        agent = StreakAgent()
        streak = _make_streak(
            current_streak=99,
            longest_streak=50,
            last_session_date=date.today() - timedelta(days=1),
            total_sessions=99,
        )
        db = _mock_db(streak)
        agent.update_streak("test-user", None, db)
        assert streak.longest_streak == 100


class TestMilestones:
    def test_milestone_7(self):
        agent = StreakAgent()
        assert agent.check_milestones_value(7) == 7

    def test_milestone_none(self):
        agent = StreakAgent()
        assert agent.check_milestones_value(8) is None

    def test_all_milestones(self):
        agent = StreakAgent()
        for m in MILESTONES:
            assert agent.check_milestones_value(m) == m


class TestStreakSave:
    def test_save_success(self):
        agent = StreakAgent()
        streak = _make_streak(
            current_streak=10,
            last_save_date=date.today() - timedelta(days=31),
        )
        db = _mock_db(streak)
        assert agent.use_save("test-user", db) is True
        assert streak.last_session_date == date.today()

    def test_save_cooldown(self):
        agent = StreakAgent()
        streak = _make_streak(
            current_streak=10,
            last_save_date=date.today() - timedelta(days=15),
        )
        db = _mock_db(streak)
        assert agent.use_save("test-user", db) is False

    def test_save_no_streak(self):
        agent = StreakAgent()
        db = _mock_db(None)
        assert agent.use_save("test-user", db) is False
