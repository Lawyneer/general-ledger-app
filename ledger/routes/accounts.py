from fastapi import APIRouter, Request
from ..database import connect
from ..services import (
    list_accounts, create_account, update_account, delete_account,
)
from ..models import AccountInput

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.get("/")
def list_accounts_route(req: Request):
    with connect() as conn:
        return list_accounts(conn)

@router.post("/")
def create_account_route(req: Request, body: AccountInput):
    with connect() as conn:
        return create_account(conn, body)

@router.patch("/{guid}")
def rename_account_route(req: Request, guid: str, body: AccountInput):
    with connect() as conn:
        return update_account(conn, guid, body)

@router.delete("/{guid}")
def delete_account_route(req: Request, guid: str):
    with connect() as conn:
        return delete_account(conn, guid)