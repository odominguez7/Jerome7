"""Tests for Pydantic request/response validation."""

import pytest
from pydantic import ValidationError

from src.api.models import (
    LogSessionRequest,
    EnergyCheckinRequest,
    FeedbackRequest,
    PledgeRequest,
)


class TestLogSessionRequest:
    def test_defaults(self):
        req = LogSessionRequest()
        assert req.duration_minutes == 7

    def test_valid_duration(self):
        req = LogSessionRequest(duration_minutes=10)
        assert req.duration_minutes == 10

    def test_negative_duration_rejected(self):
        with pytest.raises(ValidationError):
            LogSessionRequest(duration_minutes=-1)

    def test_zero_duration_rejected(self):
        with pytest.raises(ValidationError):
            LogSessionRequest(duration_minutes=0)

    def test_excessive_duration_rejected(self):
        with pytest.raises(ValidationError):
            LogSessionRequest(duration_minutes=61)

    def test_note_max_length(self):
        with pytest.raises(ValidationError):
            LogSessionRequest(note="x" * 1001)


class TestEnergyCheckinRequest:
    def test_valid_values(self):
        for val in ("low", "medium", "high"):
            req = EnergyCheckinRequest(energy=val)
            assert req.energy == val

    def test_invalid_value(self):
        with pytest.raises(ValidationError):
            EnergyCheckinRequest(energy="extreme")


class TestFeedbackRequest:
    def test_valid_feedback(self):
        req = FeedbackRequest(difficulty=3, enjoyment=5, completed_blocks=7)
        assert req.difficulty == 3

    def test_difficulty_out_of_range(self):
        with pytest.raises(ValidationError):
            FeedbackRequest(difficulty=6)

    def test_difficulty_zero_rejected(self):
        with pytest.raises(ValidationError):
            FeedbackRequest(difficulty=0)


class TestPledgeRequest:
    def test_valid_pledge(self):
        req = PledgeRequest(name="Omar", goal="focus")
        assert req.name == "Omar"

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            PledgeRequest(name="A")

    def test_name_too_long(self):
        with pytest.raises(ValidationError):
            PledgeRequest(name="x" * 101)

    def test_invalid_fitness_level(self):
        with pytest.raises(ValidationError):
            PledgeRequest(name="Omar", fitness_level="elite")

    def test_valid_fitness_levels(self):
        for level in ("beginner", "returning", "active"):
            req = PledgeRequest(name="Omar", fitness_level=level)
            assert req.fitness_level == level
