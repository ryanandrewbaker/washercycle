"""Leave-one-out evaluation on real trace fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

REAL_FIXTURES = Path(__file__).parent / "fixtures" / "real"


@pytest.mark.skipif(
    not REAL_FIXTURES.exists() or not any(REAL_FIXTURES.glob("**/*.json")),
    reason="No real trace fixtures committed yet",
)
def test_loo_evaluation_placeholder():
    """Run LOO evaluation when real fixtures are available."""
    assert True
