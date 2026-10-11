
from .database import new_guid, connect
from .models import SplitInput, TransactionInput, AccountInput
from .utils import to_cents, fmt

DEBIT_NORMAL = {"ASSET", "BANK", "CASH", "EXPENSE"}
TYPE_ORDER = {"ASSET": 1, "BANK": 1, "CASH": 1, "LIABILITY": 2, "EQUITY": 3, "INCOME": 4, "EXPENSE": 5}


def validate_and_convert_splits(conn, payload: TransactionInput, exclude_guid: str | None = None) -> list[tuple[str, int, str]]:
    """Validate splits balance and convert to signed integer cents."""
    from fastapi import HTTPException
    out = []
    for sp in payload.splits:
        if (sp.debit is None) == (sp.credit is None):
            raise HTTPException(400, "each split needs exactly one of debit/credit")
        try:
            amount = to_cents(sp.debit) if sp.debit is not None else -to_cents(sp.credit)
        except ValueError as e:
            raise HTTPException(400, str(e))
        out.append((sp.account, amount, sp.memo or ""))
    known = {r["guid"]: r["name"] for r in conn.execute("SELECT guid,name FROM accounts")}
    for guid, _, _ in out:
        if guid not in known:
            raise HTTPException(400, f"unknown account guid: {guid}")
    if sum(a for _, a, _ in out) != 0:
        delta = sum(a for _, a, _ in out)
        raise HTTPException(400, f"unbalanced_transaction: splits sum to {fmt(delta)}, expected 0.00")
    return out


def account_by_guid(conn, guid: str):
    return conn.execute("SELECT * FROM accounts WHERE guid=?", (guid,)).fetchone()


def account_exists(conn, guid: str) -> bool:
    return account_by_guid(conn, guid) is not None


def list_accounts(conn):
    rows = conn.execute("""
        SELECT a.guid, a.name, a.type, a.parent_guid,
               CASE WHEN a.type IN ('ASSET','BANK','CASH','EXPENSE')
                    THEN  COALESCE(SUM(s.amount), 0)
                    ELSE -COALESCE(SUM(s.amount), 0)
               END AS bal
        FROM accounts a
        LEFT JOIN splits s ON s.account_guid = a.guid
        GROUP BY a.guid
        ORDER BY a.type, a.name""").fetchall()
    return [{ "guid": r["guid"], "name": r["name"], "type": r["type"],
              "parent_guid": r["parent_guid"], "balance": fmt(r["bal"]) }
            for r in rows]


def create_account(conn, body: AccountInput) -> dict:
    from fastapi import HTTPException
    if not body.name or not body.name.strip():
        raise HTTPException(400, "account name is required")
    name = body.name.strip()
    if body.type not in TYPE_ORDER:
        raise HTTPException(400, f"type must be one of {sorted(TYPE_ORDER)}")
    if body.parent and not account_exists(conn, body.parent):
        raise HTTPException(400, "unknown parent guid")
    dup = conn.execute(
        """SELECT 1 FROM accounts WHERE lower(name) = lower(?) AND parent_guid IS ?""",
        (name, body.parent)).fetchone()
    if dup:
        raise HTTPException(400, f"an account named '{name}' already exists under this parent")
    guid = new_guid()
    conn.execute("INSERT INTO accounts(guid,name,type,parent_guid) VALUES(?,?,?,?)",
                 (guid, name, body.type, body.parent))
    return {"guid": guid}


def update_account(conn, guid: str, body: AccountInput) -> dict:
    from fastapi import HTTPException
    if not account_exists(conn, guid):
        raise HTTPException(404, "account not found")
    if not body.name or not body.name.strip():
        raise HTTPException(400, "account name is required")
    name = body.name.strip()
    dup = conn.execute(
        """SELECT 1 FROM accounts WHERE lower(name) = lower(?) AND parent_guid IS ? AND guid != ?""",
        (name, body.parent, guid)).fetchone()
    if dup:
        raise HTTPException(400, f"an account named '{name}' already exists under this parent")
    conn.execute("UPDATE accounts SET name=?, parent_guid=? WHERE guid=?",
                 (name, body.parent, guid))
    return {"guid": guid, "name": name}


def delete_account(conn, guid: str) -> dict:
    from fastapi import HTTPException
    if conn.execute("SELECT 1 FROM splits WHERE account_guid=?", (guid,)).fetchone():
        raise HTTPException(400, "account has transactions; cannot delete")
    if conn.execute("SELECT 1 FROM accounts WHERE parent_guid=?", (guid,)).fetchone():
        raise HTTPException(400, "account has child accounts; cannot delete")
    cur = conn.execute("DELETE FROM accounts WHERE guid=?", (guid,))
    if cur.rowcount == 0:
        raise HTTPException(404, "account not found")
    return {"deleted": guid}


def txn_to_dict(conn, guid: str):
    t = conn.execute("SELECT * FROM transactions WHERE guid=?", (guid,)).fetchone()
    if not t:
        return None
    splits = conn.execute("""
        SELECT s.*, a.name AS account_name FROM splits s
        JOIN accounts a ON a.guid = s.account_guid
        WHERE s.transaction_guid=? ORDER BY s.rowid""", (guid,)).fetchall()
    return {
        "guid": guid, "date": t["date"], "num": t["num"],
        "description": t["description"],
        "splits": [{
            "guid": s["guid"], "account": s["account_guid"],
            "account_name": s["account_name"], "memo": s["memo"],
            "amount": fmt(s["amount"]),
        } for s in splits],
    }


def create_transaction(conn, body: TransactionInput) -> dict:
    splits = validate_and_convert_splits(conn, body)
    guid = new_guid()
    conn.execute("INSERT INTO transactions(guid,date,num,description) VALUES(?,?,?,?)",
                 (guid, body.date, body.num, body.description))
    for acct, amount, memo in splits:
        conn.execute(
            "INSERT INTO splits(guid,transaction_guid,account_guid,memo,amount) VALUES(?,?,?,?,?)",
            (new_guid(), guid, acct, memo, amount))
    return txn_to_dict(conn, guid)


def update_transaction(conn, guid: str, body: TransactionInput) -> dict:
    from fastapi import HTTPException
    if not txn_to_dict(conn, guid):
        raise HTTPException(404, "transaction not found")
    splits = validate_and_convert_splits(conn, body)
    conn.execute("UPDATE transactions SET date=?,num=?,description=? WHERE guid=?",
                 (body.date, body.num, body.description, guid))
    conn.execute("DELETE FROM splits WHERE transaction_guid=?", (guid,))
    for acct, amount, memo in splits:
        conn.execute(
            "INSERT INTO splits(guid,transaction_guid,account_guid,memo,amount) VALUES(?,?,?,?,?)",
            (new_guid(), guid, acct, memo, amount))
    return txn_to_dict(conn, guid)


def delete_transaction(conn, guid: str) -> dict:
    from fastapi import HTTPException
    conn.execute("DELETE FROM splits WHERE transaction_guid=?", (guid,))
    cur = conn.execute("DELETE FROM transactions WHERE guid=?", (guid,))
    if cur.rowcount == 0:
        raise HTTPException(404, "transaction not found")
    return {"deleted": guid}


def query_journal(conn, from_: str | None, to: str | None, page: int, size: int) -> dict:
    from fastapi import HTTPException
    if page < 1 or size < 1 or size > 1000:
        raise HTTPException(400, "page must be >=1 and size in 1..1000")
    where, params = [], []
    if from_:
        where.append("t.date >= ?"); params.append(from_)
    if to:
        where.append("t.date <= ?"); params.append(to)
    cond = ("WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(f"""
        SELECT t.guid FROM transactions t {cond}
        ORDER BY t.date DESC, t.rowid DESC LIMIT ? OFFSET ?""",
        (*params, size + 1, (page - 1) * size)).fetchall()
    has_more = len(rows) > size
    txns = [txn_to_dict(conn, r["guid"]) for r in rows[:size]]
    return {"transactions": txns, "page": page, "has_more": has_more}


def sums_as_of(conn, as_of: str | None, types: tuple) -> list:
    if as_of is None:
        as_of = "9999-12-31"
    placeholders = ",".join("?" * len(types))
    return conn.execute(f"""
        SELECT a.guid, a.name, a.type,
               COALESCE(SUM(CASE WHEN t.date IS NULL OR t.date <= ?
                                THEN s.amount END), 0) AS bal
        FROM accounts a
        LEFT JOIN splits s       ON s.account_guid = a.guid
        LEFT JOIN transactions t ON t.guid = s.transaction_guid
        WHERE a.type IN ({placeholders})
        GROUP BY a.guid, a.name, a.type""", (as_of, *types)).fetchall()


def trial_balance_data(conn, as_of: str | None):
    rows = sums_as_of(conn, as_of,
                       ("ASSET", "BANK", "CASH", "LIABILITY", "EQUITY", "INCOME", "EXPENSE"))
    lines, td, tc = [], 0, 0
    for r in sorted(rows, key=lambda r: (TYPE_ORDER[r["type"]], r["name"])):
        if r["bal"] == 0:
            continue
        debit = r["bal"] if r["type"] in DEBIT_NORMAL else None
        credit = -r["bal"] if r["type"] not in DEBIT_NORMAL else None
        if debit is not None:
            td += r["bal"]
        if credit is not None:
            tc += -r["bal"]
        lines.append({"account": r["name"], "type": r["type"],
                      "debit": debit, "credit": credit})
    return lines, td, tc


def income_statement_data(conn, frm: str, to: str):
    def rows(typ, sign):
        return [{"account": r["name"], "amount": fmt(sign * r["s"])}
                for r in conn.execute("""
                    SELECT a.name, SUM(s.amount) AS s
                    FROM splits s
                    JOIN transactions t ON t.guid = s.transaction_guid
                    JOIN accounts a     ON a.guid = s.account_guid
                    WHERE a.type = ? AND t.date BETWEEN ? AND ?
                    GROUP BY a.guid HAVING s <> 0 ORDER BY a.name""",
                    (typ, frm, to))]
    income, expenses = rows("INCOME", -1), rows("EXPENSE", 1)
    ti = sum(int(x["amount"].replace(",", "").replace(".", "")) for x in income)
    te = sum(int(x["amount"].replace(",", "").replace(".", "")) for x in expenses)
    return {"income": income, "expenses": expenses,
            "total_income": fmt(ti), "total_expenses": fmt(te),
            "net_income": fmt(ti - te)}


def balance_sheet_data(conn, as_of: str | None):
    assets = [r for r in sums_as_of(conn, as_of, ("ASSET", "BANK", "CASH")) if r["bal"]]
    liabs = [r for r in sums_as_of(conn, as_of, ("LIABILITY",)) if r["bal"]]
    equity = [r for r in sums_as_of(conn, as_of, ("EQUITY",)) if r["bal"]]
    inc_exp = conn.execute("""
        SELECT COALESCE(SUM(CASE WHEN a.type='INCOME'  THEN s.amount END),0) AS i,
               COALESCE(SUM(CASE WHEN a.type='EXPENSE' THEN s.amount END),0) AS x
        FROM splits s
        JOIN transactions t ON t.guid = s.transaction_guid
        JOIN accounts a     ON a.guid = s.account_guid
        WHERE t.date <= ?""", (as_of or "9999-12-31",)).fetchone()
    a = sum(r["bal"] for r in assets)
    l = sum(r["bal"] for r in liabs)
    e = sum(r["bal"] for r in equity)
    earnings = -(inc_exp["i"] + inc_exp["x"])
    return {
        "as_of": as_of,
        "assets": [{"account": r["name"], "amount": fmt(r["bal"])} for r in assets],
        "liabilities": [{"account": r["name"], "amount": fmt(-r["bal"])} for r in liabs],
        "equity": [{"account": r["name"], "amount": fmt(-r["bal"])} for r in equity]
                  + [{"account": "Current Earnings", "amount": fmt(earnings)}],
        "total_assets": fmt(a), "total_liabilities": fmt(-l),
        "total_equity": fmt(-e + earnings),
        "balanced": a == -(l + e) + earnings,
    }


def cash_flow_data(conn, frm: str, to: str):
    cash_ids = {r["guid"] for r in conn.execute(
        "SELECT guid FROM accounts WHERE type IN ('BANK','CASH')")}
    groups = {}
    for t in conn.execute("""
            SELECT t.guid, s.account_guid, s.amount, a.name, a.type
            FROM transactions t
            JOIN splits s ON s.transaction_guid = t.guid
            JOIN accounts a ON a.guid = s.account_guid
            WHERE t.date BETWEEN ? AND ? ORDER BY t.date""", (frm, to)):
        groups.setdefault(t["guid"], []).append(t)
    inflows, outflows = {}, {}
    for txns in groups.values():
        delta = sum(r["amount"] for r in txns if r["account_guid"] in cash_ids)
        if delta == 0:
            continue
        counters = {(r["name"], r["type"]) for r in txns if r["account_guid"] not in cash_ids}
        key = counters.pop() if len(counters) == 1 else ("(multi-split)", "OTHER")
        bucket = inflows if delta > 0 else outflows
        bucket[key] = bucket.get(key, 0) + abs(delta)
    def lines(d):
        return [{"category": k[0], "type": k[1], "amount": fmt(v)}
                for k, v in sorted(d.items(), key=lambda kv: -abs(kv[1]))]
    bal = conn.execute("""
        SELECT COALESCE(SUM(CASE WHEN t.date <  :f THEN s.amount END),0) AS begin,
               COALESCE(SUM(CASE WHEN t.date <= :t THEN s.amount END),0) AS end
        FROM splits s JOIN transactions t ON t.guid = s.transaction_guid
        WHERE s.account_guid IN (SELECT guid FROM accounts
                                 WHERE type IN ('BANK','CASH'))""",
        {"f": frm, "t": to}).fetchone()
    return {"inflows": lines(inflows), "outflows": lines(outflows),
            "cash_begin": fmt(bal["begin"]), "cash_end": fmt(bal["end"]),
            "net_change_cash": fmt(bal["end"] - bal["begin"])}