# main.py

"""
BUSINESS SYSTEM (BuSy)

A customized system designed for short business that 
need to automate and do regular stuff. This system
has been developed for a children's boutique.
- 4 shops (POS).
- 1 online shop.
- Inventory synchronization.
- Self managed static files: Stored media and databases.
"""

# Import libraries
from fastapi import FastAPI

# Import modules
from databases.createdb import create_sqlite_database
from databases.singleton import init_sqlite
from routers.auth import auth

app: FastAPI = FastAPI()
app.include_router(auth)

@app.on_event("startup")
def _startup_create_db() -> None:
    try:
        create_sqlite_database("databases/busy.sqlite3")
    except FileExistsError:
        pass
    init_sqlite("databases/busy.sqlite3")

@app.get
async def ison():
    return {"response": "Yes, I'm on."}
