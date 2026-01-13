# userconf.py

"""
Incluye los endpoints para implementar la app /userconf
"""

# Importar librerias
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from typing import Any
import json

# Importar modulos
from routers.authentication import current_user, User, crypt
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
        email=user_db.get("email"),
        typeUser=user_db["user_type"],
    )

# Create User
@router_userconf.post("/create_user:{userinfo}") # Userinfo deberá ser un diccionario.
async def create_user(userinfo, user: User = Depends(current_user)):
    if user.typeUser not in (1, 2): # Salir si el usuario no es admin o superadmin
        raise HTTPException(status_code=403, detail="Not authorized to access user info")
    
    # 1. Obtiene la información del usuario
    # 2. Realiza la query pertinente a la base de datos
    # 3. Retorna mensaje de éxito
    if isinstance(userinfo, str):
        try:
            userinfo = json.loads(userinfo)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid user info format") from exc

    if not isinstance(userinfo, dict):
        raise HTTPException(status_code=400, detail="User info must be a dictionary")

    username = (userinfo.get("username") or "").strip()
    fullname = (userinfo.get("fullname") or "").strip()
    type_user = userinfo.get("typeUser")
    password = userinfo.get("pw") or userinfo.get("password")

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if not fullname:
        raise HTTPException(status_code=400, detail="Fullname is required")
    if type_user in (None, ""):
        raise HTTPException(status_code=400, detail="typeUser is required")
    if password in (None, ""):
        raise HTTPException(status_code=400, detail="Password is required")

    try:
        type_user = int(type_user)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid typeUser") from exc

    birthday = userinfo.get("birthday")
    if birthday in (None, ""):
        birthday_value = None
    else:
        parsed_birthday = _parse_birthday(birthday)
        if parsed_birthday is None:
            raise HTTPException(status_code=400, detail="Invalid birthday format")
        birthday_value = parsed_birthday.isoformat()

    cellphone = userinfo.get("cellphone")
    if cellphone in (None, ""):
        cellphone_value = None
    else:
        try:
            cellphone_value = int(cellphone)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid cellphone") from exc

    email = (userinfo.get("email") or "").strip() or None
    rfc = (userinfo.get("rfc") or "").strip() or None

    database = Database()
    existing = database.fetch_query(
        "SELECT id FROM users WHERE username = ?",
        (username,),
    )
    if existing is None:
        raise HTTPException(status_code=500, detail="Database query failed")
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists")

    hashed_password = crypt.hash(password)
    database.execute_query(
        """
        INSERT INTO users (user_type, username, fullname, cellphone, email, birthday, rfc, password)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            type_user,
            username,
            fullname,
            cellphone_value,
            email,
            birthday_value,
            rfc,
            hashed_password,
        ),
    )

    return {"message": "User created successfully"}

# Edit user
@router_userconf.post("/edit_user:{userinfo}") # Userinfo deberá ser un diccionario.
async def edit_user(userinfo, user: User = Depends(current_user)):
    if user.typeUser not in (1, 2):
        raise HTTPException(status_code=403, detail="Not authorized to access user info")
    # AGREGAR: No permitir que un usuario admin (2), elimine a un superadmin (1)
    # 1. Obtiene la información del usuario
    # 2. Realiza la query pertinente a la base de datos
    # 3. Retorna mensaje de éxito o error
    if isinstance(userinfo, str):
        try:
            userinfo = json.loads(userinfo)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Invalid user info format") from exc

    if not isinstance(userinfo, dict):
        raise HTTPException(status_code=400, detail="User info must be a dictionary")

    target_id = userinfo.get("id")
    target_username = userinfo.get("username")
    if target_id is None and not target_username:
        raise HTTPException(status_code=400, detail="Missing user identifier")

    database = Database()
    if target_id is not None:
        rows = database.fetch_query("SELECT * FROM users WHERE id = ?", (target_id,))
    else:
        rows = database.fetch_query(
            "SELECT * FROM users WHERE username = ?",
            (target_username,),
        )

    if rows is None:
        raise HTTPException(status_code=500, detail="Database query failed")
    if not rows:
        raise HTTPException(status_code=404, detail="User not found")

    target_user = rows[0]
    if user.typeUser == 2 and target_user.get("user_type") == 1:
        raise HTTPException(status_code=403, detail="Not authorized to edit this user")

    updates: dict[str, Any] = {}

    if "username" in userinfo:
        username = (userinfo.get("username") or "").strip()
        if not username:
            raise HTTPException(status_code=400, detail="Username is required")
        updates["username"] = username

    if "fullname" in userinfo:
        fullname = (userinfo.get("fullname") or "").strip()
        if not fullname:
            raise HTTPException(status_code=400, detail="Fullname is required")
        updates["fullname"] = fullname

    if "birthday" in userinfo:
        birthday = userinfo.get("birthday")
        if birthday in (None, ""):
            updates["birthday"] = None
        else:
            parsed_birthday = _parse_birthday(birthday)
            if parsed_birthday is None:
                raise HTTPException(status_code=400, detail="Invalid birthday format")
            updates["birthday"] = parsed_birthday.isoformat()

    if "rfc" in userinfo:
        rfc = (userinfo.get("rfc") or "").strip()
        updates["rfc"] = rfc or None

    if "cellphone" in userinfo:
        cellphone = userinfo.get("cellphone")
        if cellphone in (None, ""):
            updates["cellphone"] = None
        else:
            try:
                updates["cellphone"] = int(cellphone)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=400, detail="Invalid cellphone") from exc

    if "email" in userinfo:
        email = (userinfo.get("email") or "").strip()
        updates["email"] = email or None

    if "typeUser" in userinfo:
        type_user = userinfo.get("typeUser")
        if type_user in (None, ""):
            raise HTTPException(status_code=400, detail="typeUser is required")
        try:
            updates["user_type"] = int(type_user)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid typeUser") from exc

    if "pw" in userinfo:
        password = userinfo.get("pw")
        if password not in (None, ""):
            updates["password"] = crypt.hash(password)

    if "password" in userinfo:
        password = userinfo.get("password")
        if password not in (None, ""):
            updates["password"] = crypt.hash(password)

    if not updates:
        raise HTTPException(status_code=400, detail="No changes provided")

    set_clause = ", ".join(f"{column} = ?" for column in updates)
    params = list(updates.values())
    if target_id is not None:
        params.append(target_id)
        where_clause = "id = ?"
    else:
        params.append(target_username)
        where_clause = "username = ?"

    database.execute_query(
        f"UPDATE users SET {set_clause} WHERE {where_clause}",
        tuple(params),
    )

    return {"message": "User updated successfully"}

# Delete user
@router_userconf.post("/delete_user:{username}") # Userinfo deberá ser un diccionario.
async def delete_user(username, user: User = Depends(current_user)):
    # NOTA: El usuario de tipo 1 es el de más privilegios y el de tipo 5 el de menor privilegios. Evita que un usuario pueda eliminar a otro de mayor privilegios 
    # 1. Obtiene la información del usuario
    # 2. Realiza la query pertinente a la base de datos
    # 3. Retorna mensaje de éxito
    if user.typeUser not in (1, 2):
        raise HTTPException(status_code=403, detail="Not authorized to access user info")

    if not isinstance(username, str) or not username.strip():
        raise HTTPException(status_code=400, detail="Username is required")

    database = Database()
    rows = database.fetch_query(
        "SELECT id, user_type FROM users WHERE username = ?",
        (username.strip(),),
    )

    if rows is None:
        raise HTTPException(status_code=500, detail="Database query failed")
    if not rows:
        raise HTTPException(status_code=404, detail="User not found")

    target_user = rows[0]
    target_type = target_user.get("user_type")
    if target_type is None:
        raise HTTPException(status_code=500, detail="User type not found")

    #if user.typeUser > target_type:
       # raise HTTPException(status_code=403, detail="Not authorized to delete this user")

    database.execute_query(
        "DELETE * FROM users WHERE id = ?",
        (target_user["id"],),
    )

    return {"message": "User deleted successfully"}
