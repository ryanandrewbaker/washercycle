"""Tests for training recorder."""

from __future__ import annotations

import pytest

from custom_components.washercycle.training import TrainingRecorder


def test_start_and_cancel():
    rec = TrainingRecorder()
    run_id = rec.start("daily_wash")
    assert rec.is_active
    assert run_id
    rec.cancel()
    assert not rec.is_active


def test_cannot_start_twice():
    rec = TrainingRecorder()
    rec.start("daily_wash")
    with pytest.raises(ValueError):
        rec.start("quick_wash")


def test_mark_complete_requires_active():
    rec = TrainingRecorder()
    with pytest.raises(ValueError):
        rec.mark_complete_and_save()
