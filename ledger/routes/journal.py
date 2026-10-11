
from fastapi import APIRouter, Request, Query
from ..database import connect
from ..services import (
    query_journal, create_transaction, update_transaction, delete_transaction
)
from ..models import TransactionInput

router = APIRouter(prefix="/journal", tags=["journal"])


@router.get("/")
def list_journal(req: Request, from_: str | None = Query(None, alias="from"),
                 to: str | None = None, page: int = 1, size: int = 100):
    with connect() as conn:
        return query_journal(conn, from_, to, page, size)


@router.get("/{guid}")
def get_txn(req: Request, guid: str):
    from fastapi import HTTPException
    from ..services import txn_to_dict
    with connect() as conn:
        result = txn_to_dict(conn, guid)
        if not result:
            raise HTTPException(404, "transaction not found")
        return result


@router.post("/")
def create_txn(req: Request, body: TransactionInput):
    with connect() as conn:
        return create_transaction(conn, body)


@router.put("/{guid}")
def update_txn(req: Request, guid: str, body: TransactionInput):
    with connect() as conn:
        return update_transaction(conn, guid, body)


@router.delete("/{guid}")
def delete_txn(req: Request, guid: str):
    with connect() as conn:
        return delete_transaction(conn, guid)