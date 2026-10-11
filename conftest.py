"""Pytest fixtures: point the ledger at a throwaway temp database."""

import pytest

import ledger.database as db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Every test gets a fresh, empty database in a temp directory."""
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    yield