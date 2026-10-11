
from fastapi import APIRouter, Request, Query
from fastapi.responses import Response
from ..database import connect
from ..services import trial_balance_data, income_statement_data, balance_sheet_data, cash_flow_data
from ..utils import fmt, make_xlsx

router = APIRouter(prefix="/statements", tags=["statements"])


@router.get("/trial-balance")
def trial_balance(req: Request, as_of: str | None = Query(None)):
    with connect() as conn:
        lines, td, tc = trial_balance_data(conn, as_of)
        return {"as_of": as_of,
                "lines": [{"account": l["account"], "type": l["type"],
                           "debit": fmt(l["debit"]) if l["debit"] is not None else None,
                           "credit": fmt(l["credit"]) if l["credit"] is not None else None}
                          for l in lines],
                "total_debits": fmt(td), "total_credits": fmt(tc),
                "balanced": td == tc}


@router.get("/trial-balance/excel")
def trial_balance_excel(req: Request, as_of: str | None = Query(None)):
    with connect() as conn:
        lines, td, tc = trial_balance_data(conn, as_of)
    rows = [[l["account"], l["type"],
             (l["debit"] / 100) if l["debit"] is not None else "",
             (l["credit"] / 100) if l["credit"] is not None else ""]
            for l in lines]
    rows.append(["Totals", "", td / 100, tc / 100])
    xlsx = make_xlsx("Trial Balance", ["Account", "Type", "Debit", "Credit"], rows)
    filename = f"trial-balance{'-' + as_of if as_of else ''}.xlsx"
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/income-statement")
def income_statement(req: Request, frm: str = Query(..., alias="from"), to: str = Query(...)):
    with connect() as conn:
        d = income_statement_data(conn, frm, to)
        return {"from": frm, "to": to, **d}


@router.get("/balance-sheet")
def balance_sheet(req: Request, as_of: str | None = Query(None)):
    with connect() as conn:
        return balance_sheet_data(conn, as_of)


@router.get("/cash-flow")
def cash_flow(req: Request, frm: str = Query(..., alias="from"), to: str = Query(...)):
    with connect() as conn:
        d = cash_flow_data(conn, frm, to)
        return {"from": frm, "to": to, **d}