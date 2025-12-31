# userconf.py

"""
Incluye los endpoints para implementar la app /userconf
"""

# Importar librerias
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from typing import Any

# Importar modulos
from routers.authentication import current_user, User
from databases.singleton import Database

router_prefix: str = "/userconf"
# Crear instancia de router
router_userconf: APIRouter = APIRouter(prefix= router_prefix)



"""
ENDPOINTS
"""

# Is active?
@router_userconf.get("/ison")
async def ison():
    return {
        "message": f"Yes, I'm on from '{router_prefix}'"
    }

# Search user
@router_userconf.get("/search_byusername/{username}", response_model=list[str])
async def search_users_by_username(
    username: str,
    limit: int = Query(10, ge=1, le=50),
    user: User = Depends(current_user),
):
    # Para uso bajo demanda entre las apps de este servidor.
    # 1. Entra un parámetro de búsqueda
    # 2. Hace la query con ese parámetro
    # 3. Devuelve una lista con las coincidencias
    search_term = username.strip()
    if not search_term:
        return []

    database = Database()
    rows = database.fetch_query(
        """
        SELECT DISTINCT u.username
        FROM users u
        JOIN user_type ut ON ut.id = u.user_type
        WHERE ut.type != ?
          AND u.username LIKE ? COLLATE NOCASE
        ORDER BY u.username
        LIMIT ?
        """,
        ("customer", f"%{search_term}%", limit),
    )

    if rows is None:
        raise HTTPException(status_code=500, detail="Database query failed")

    return [row["username"] for row in rows if row.get("username")]

def _parse_birthday(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None

# get_userinfo
@router_userconf.get("/get_userinfo/{username}", response_model=User)
async def get_userinfo(
    username: str,
    user: User = Depends(current_user),
):
    if user.typeUser not in (1, 2, 3):
        raise HTTPException(status_code=403, detail="Not authorized to access user info")

    database = Database()
    rows = database.fetch_query(
        "SELECT * FROM users WHERE username = ?",
        (username,),
    )

    if rows is None:
        raise HTTPException(status_code=500, detail="Database query failed")
    if not rows:
        raise HTTPException(status_code=404, detail="User not found")

    user_db = rows[0]
    return User(
        id=user_db["id"],
        username=user_db["username"],
        fullname=user_db["fullname"],
        birthday=_parse_birthday(user_db.get("birthday")),
        rfc=user_db.get("rfc"),
        cellphone=user_db.get("cellphone"),
        typeUser=user_db["user_type"],
    )

# Create User
@router_userconf.post("/create_user:{userinfo}") # Userinfo deberá ser un diccionario.
async def create_user(userinfo, user: User = Depends(current_user)):
    # 1. Obtiene la información del usuario
    # 2. Realiza la query pertinente a la base de datos
    # 3. Retorna mensaje de éxito
    pass

# Edit user
@router_userconf.post("/edit_user:{userinfo}") # Userinfo deberá ser un diccionario.
async def edit_user(userinfo, user: User = Depends(current_user)):
    # 1. Obtiene la información del usuario
    # 2. Realiza la query pertinente a la base de datos
    # 3. Retorna mensaje de éxito
    pass

# Delete user
@router_userconf.post("/delete_user:{username}") # Userinfo deberá ser un diccionario.
async def delete_user(username, user: User = Depends(current_user)):
    # 1. Obtiene la información del usuario
    # 2. Realiza la query pertinente a la base de datos
    # 3. Retorna mensaje de éxito
    pass
