from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class Prompt(BaseModel):
    text: str
    run_id: Optional[str] = None


class Thread(BaseModel):
    id: str
    created: datetime


class Answer(BaseModel):
    text: str
