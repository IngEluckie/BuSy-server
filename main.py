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
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Import modules
from databases.singleton import Database
from routers import authentication, userconf

# Server's instance, routers & middleware.
app: FastAPI = FastAPI()
app.include_router(authentication.router_authentication)
app.include_router(userconf.router_userconf)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # O especifica tu dominio 'http://localhost:5500', etc.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

"""
Eventos para la base de datos
"""
@app.on_event("startup")
def startup_event():
    db = Database()  # Esto inicializa la conexión al iniciar la app

@app.on_event("shutdown")
def shutdown_event():
    db = Database()
    db.close_connection()
"""
-----------------------------
"""

@app.get("/ison")
async def ison():
    return {
        "message" : "Yes, I'm working!"
    }


#Esta parte se deja hasta el final de este script
#  Por cómo funcionan las direcciones por defecto en FastAPI
#app.mount("/dev", StaticFiles(directory="static/public/dev", html=True), name="dev")
app.mount("/", StaticFiles(directory="static/public", html=True), name="public")
#app.mount("/", StaticFiles(directory="static/public", html=True), name="static")

#Documentation on Swagger: http://127.0.0.1:8000/docs
#Documentation on Redocly: http://127.0.0.1:8000/redoc

#Inicia el servidor: uvicorn server:app --reload
#uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Para MacOS
#ipconfig getifaddr en0 
