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
from routers.auth import auth

app: FastAPI = FastAPI()
app.include_router(auth)

@app.get
async def ison():
    return {"response": "Yes, I'm on."}