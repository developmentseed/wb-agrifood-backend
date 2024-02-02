from pydantic import BaseModel


class Prompt(BaseModel):
    text: str


class Answer(BaseModel):
    text: str
