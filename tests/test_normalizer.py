"""Tests for input normalizer."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.washercycle.normalizer import InputNormalizer


def test_missing_power_returns_none():
    n = InputNormalizer()
    assert n.normalize_power("sensor.power", "unavailable", datetime.now(UTC)) is None


def test_negative_power_rejected():
    n = InputNormalizer()
    result = n.normalize_power("sensor.power", "-5", datetime.now(UTC))
    assert result is None
    assert len(n.state.rejected) == 1


def test_energy_kwh_converted_to_wh():
    n = InputNormalizer()
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    result = n.normalize_energy("sensor.energy", "1.5", ts, energy_in_kwh=True)
    assert result is not None
    assert result.watt_hours == 1500.0


def test_unknown_not_treated_as_zero():
    n = InputNormalizer()
    result = n.normalize_power("sensor.power", "unknown", datetime.now(UTC))
    assert result is None


def test_door_on_means_open():
    n = InputNormalizer()
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    result = n.normalize_bool("binary_sensor.laundry_washerdoor_contact", "on", ts)
    assert result is not None
    assert result.value is True


def test_energy_reset_detected():
    n = InputNormalizer()
    ts1 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    ts2 = datetime(2026, 1, 1, 10, 1, tzinfo=UTC)
    n.normalize_energy("sensor.energy", "10.0", ts1, energy_in_kwh=True)
    result = n.normalize_energy("sensor.energy", "0.1", ts2, energy_in_kwh=True)
    assert result is not None
    assert result.reset_detected is True
