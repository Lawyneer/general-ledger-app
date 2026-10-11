"""
Core accounting invariant tests for Ledger.

These three tests guard the most important property of the application:
the books must always balance. Every journal entry is forced to have
debits equal to credits, and the trial balance must therefore tie.
"""

import pytest
from fastapi import HTTPException

from ledger.database import connect
from ledger.models import SplitInput, TransactionInput
from ledger.services import create_transaction, trial_balance_data


def _guid(conn, name: str) -> str:
    """Look up an account GUID by name in the seeded chart of accounts."""
    row = conn.execute("SELECT guid FROM accounts WHERE name=?", (name,)).fetchone()
    assert row is not None, f"seed account not found: {name}"
    return row["guid"]


def _paycheck(amount: str = "2000.00"):
    """A standard balanced entry: salary paid into checking."""
    return {
        "date": "2026-10-01",
        "description": "Paycheck",
        "splits": [
            {"debit": amount},   # filled in per-test with real GUIDs
            {"credit": amount},
        ],
    }


def test_balanced_entry_is_accepted():
    """A debits-equal-credits entry must be created successfully."""
    with connect() as conn:
        checking = _guid(conn, "Checking")
        salary = _guid(conn, "Salary")
        txn_in = TransactionInput(
            date="2026-10-01",
            description="Paycheck",
            splits=[
                SplitInput(account=checking, debit="2000.00"),
                SplitInput(account=salary, credit="2000.00"),
            ],
        )
        result = create_transaction(conn, txn_in)

        assert result is not None
        assert result["description"] == "Paycheck"
        assert len(result["splits"]) == 2
        # Amounts come back as formatted strings; parse and check signs.
        # Debit to Checking is positive, credit to Salary is negative.
        amounts = [float(s["amount"].replace(",", "")) for s in result["splits"]]
        assert sum(amounts) == 0
        assert 2000.00 in amounts
        assert -2000.00 in amounts


def test_unbalanced_entry_is_rejected():
    """An entry whose debits and credits differ must be rejected outright."""
    with connect() as conn:
        checking = _guid(conn, "Checking")
        salary = _guid(conn, "Salary")
        txn_in = TransactionInput(
            date="2026-10-02",
            description="Broken entry",
            splits=[
                SplitInput(account=checking, debit="10.00"),
                SplitInput(account=salary, credit="5.00"),
            ],
        )
        with pytest.raises(HTTPException) as exc_info:
            create_transaction(conn, txn_in)
        assert exc_info.value.status_code == 400
        assert "unbalanced" in exc_info.value.detail.lower()


def test_trial_balance_ties():
    """After posting several entries, total debits must equal total credits."""
    with connect() as conn:
        checking = _guid(conn, "Checking")
        salary = _guid(conn, "Salary")
        expenses = _guid(conn, "Expenses")

        create_transaction(conn, TransactionInput(
            date="2026-10-01", description="Paycheck",
            splits=[SplitInput(account=checking, debit="2000.00"),
                    SplitInput(account=salary, credit="2000.00")]))
        create_transaction(conn, TransactionInput(
            date="2026-10-02", description="Groceries",
            splits=[SplitInput(account=expenses, debit="150.00"),
                    SplitInput(account=checking, credit="150.00")]))

        _lines, total_debits, total_credits = trial_balance_data(conn, None)

        assert total_debits > 0                  # actually exercised the book
        assert total_debits == total_credits      # and it ties