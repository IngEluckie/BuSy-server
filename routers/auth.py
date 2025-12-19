# auth.py

# Import libraries
from fastapi import APIRouter
from pydantic import BaseModel

auth: APIRouter = APIRouter(prefix="/authentication")

@auth.get
async def ison():
    return {"response": "Yes, I'm on"}