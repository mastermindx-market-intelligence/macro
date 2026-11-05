"""Hermetic test defaults for deployment-only storage settings."""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_external_storage_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Do not let the host's production .env bind tmp-path tests to the SSD.

    Tests that exercise the external-storage guard explicitly set these values
    after this fixture runs. Empty values also prevent python-dotenv from
    repopulating them from the deployment .env during Config.from_env().
    """
    for name in (
        "MARKETDESK_STORAGE_VOLUME",
        "MARKETDESK_STORAGE_ROOT",
        "MARKETDESK_STORAGE_VOLUME_UUID",
        "MARKETDESK_STORAGE_MIN_FREE_GIB",
    ):
        monkeypatch.setenv(name, "")
