from pydantic import BaseModel


class DaxPrompt(BaseModel):
    prompt: str


class DaxFormula(BaseModel):
    dax: str
