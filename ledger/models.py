
from pydantic import BaseModel, field_validator


class SplitInput(BaseModel):
    account: str
    debit: str | None = None
    credit: str | None = None
    memo: str = ""


class TransactionInput(BaseModel):
    date: str
    description: str = ""
    num: str = ""
    splits: list[SplitInput]

    @field_validator("splits")
    @classmethod
    def at_least_two(cls, v):
        if len(v) < 2:
            raise ValueError("a journal entry needs at least 2 splits")
        return v


class AccountInput(BaseModel):
    name: str
    type: str
    parent: str | None = None