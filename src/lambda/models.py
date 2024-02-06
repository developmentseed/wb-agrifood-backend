from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Prompt(BaseModel):
    message: str
    run_id: Optional[str] = None


class Thread(BaseModel):
    id: str
    created: datetime


class Run(BaseModel):
    id: str
    thread_id: str


class Answer(BaseModel):
    text: str
