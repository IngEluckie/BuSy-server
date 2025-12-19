# auth.py

# Import libraries
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

auth: APIRouter = APIRouter(prefix="/authentication")

class User(BaseModel):
    id: int
    username: str | None # En su defecto se puede usar el fullname
    fullname: str
    birthday: datetime | None
    rfc: str | None
    cellphone: int | None

class PrivateUser(User):
    pw: str

@auth.get
async def ison():
    return {"response": "Yes, I'm on"}