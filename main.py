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
from multiprocessing import Event, Process
from multiprocessing.synchronize import Event as EventType
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Import modules
from databases.singleton import Database
from routers import authentication, respaldos, userconf
from routers.pos_operations.operaciones import articulos
from utilities.handleDocument.document import BusyPaths
from utilities.scheduler.scheduler import Scheduler
from utilities.terminalTools import CsvManager, Logger

# Server's instance, routers & middleware.
app: FastAPI = FastAPI()
app.include_router(authentication.router_authentication)
app.include_router(userconf.router_userconf)
app.include_router(respaldos.router_respaldos)
app.include_router(articulos.router_articulos)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # O especifica tu dominio 'http://localhost:5500', etc.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()

def run_scheduler_process(stop_event: EventType) -> None:
    scheduler: Scheduler = Scheduler()
    scheduler.run(stop_event=stop_event)

"""
Eventos para la base de datos
"""

logs_doc: CsvManager = CsvManager("System_event_logs_document")
logger: Logger = Logger(logs_doc, debug_enabled= False)

@app.on_event("startup")
def startup_event():
    try:
        db = Database()  # Esto inicializa la conexión al iniciar la app
        scheduler_stop_event = Event()
        scheduler_process = Process(
            target=run_scheduler_process,
            args=(scheduler_stop_event,),
            name="busy-scheduler-process",
            daemon=True
        )
        scheduler_process.start()
        app.state.scheduler_stop_event = scheduler_stop_event
        app.state.scheduler_process = scheduler_process
        logger.info(f"Scheduler iniciado en proceso PID={scheduler_process.pid}")
    except Exception as e:
        logger.error(f"¡Ups! Error encontrado: {e}")
        pass # Siento que quiero agregarle algo más

    logger.success("El servidor ha sido inicializado exitosamente...")

@app.on_event("shutdown")
def shutdown_event():
    scheduler_stop_event = getattr(app.state, "scheduler_stop_event", None)
    scheduler_process = getattr(app.state, "scheduler_process", None)

    if scheduler_stop_event is not None:
        scheduler_stop_event.set()

    if scheduler_process is not None and scheduler_process.is_alive():
        scheduler_process.join(timeout=5)
        if scheduler_process.is_alive():
            scheduler_process.terminate()

    db = Database()
    db.close_connection()
    logger.info("Servicio terminado... ¡Adios!")

    busy_paths = BusyPaths()
    busy_paths.flush_archive()
    busy_paths.cleanup()
    
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
