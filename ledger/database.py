
import sqlite3
import uuid
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "ledger.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    guid        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL,
    parent_guid TEXT REFERENCES accounts(guid),
    created_at  TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS transactions (
    guid        TEXT PRIMARY KEY,
    date        TEXT NOT NULL,
    num         TEXT DEFAULT '',
    description TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS splits (
    guid             TEXT PRIMARY KEY,
    transaction_guid TEXT NOT NULL REFERENCES transactions(guid) ON DELETE CASCADE,
    account_guid     TEXT NOT NULL REFERENCES accounts(guid),
    memo             TEXT DEFAULT '',
    amount           INTEGER NOT NULL,
    reconcile_state  TEXT DEFAULT 'n'
);
CREATE INDEX IF NOT EXISTS idx_splits_txn    ON splits(transaction_guid);
CREATE INDEX IF NOT EXISTS idx_splits_acct   ON splits(account_guid);
CREATE INDEX IF NOT EXISTS idx_txn_date      ON transactions(date);
"""

SEED_ACCOUNTS = [
    ("Assets", "ASSET", None),
    ("Assets:Checking", "BANK", "Assets"),
    ("Assets:Cash", "CASH", "Assets"),
    ("Liabilities", "LIABILITY", None),
    ("Equity", "EQUITY", None),
    ("Equity:Opening Balances", "EQUITY", "Equity"),
    ("Income", "INCOME", None),
    ("Income:Salary", "INCOME", "Income"),
    ("Expenses", "EXPENSE", None),
    ("Expenses:Groceries", "EXPENSE", "Expenses"),
    ("Expenses:Utilities", "EXPENSE", "Expenses"),
]


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0:
            ids = {}
            for name, typ, parent in SEED_ACCOUNTS:
                guid = uuid.uuid4().hex
                ids[name] = guid
                conn.execute(
                    "INSERT INTO accounts(guid,name,type,parent_guid) VALUES(?,?,?,?)",
                    (guid, name.split(":")[-1], typ, ids.get(parent)))
    print(f"[ledger] database ready: {DB_PATH}")


def new_guid():
    return uuid.uuid4().hex