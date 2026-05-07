# ventas.py

# Import libraries
from fastapi import APIRouter, HTTPException, Depends, status

# Import modules
from databases.singleton import Database

# Iniciar router
router_ventas = APIRouter(prefix="/ventas") 