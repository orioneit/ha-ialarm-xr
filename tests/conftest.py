"""Fixtures."""

from __future__ import annotations

import pytest

from .fake_cloud import FakeCloud


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
async def cloud(socket_enabled):
    fake = FakeCloud()
    await fake.start()
    yield fake
    await fake.stop()
