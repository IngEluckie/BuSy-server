# auth.py

# Import libraries
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from typing import Any

# Import database singleton
from databases.singleton import Database

# Iniciar router
router_authentication = APIRouter(prefix="/auth")

# Cargar variables de entorno
load_dotenv()

class User(BaseModel):
    id: int
    username: str | None # En su defecto se puede usar el fullname
    fullname: str
    birthday: datetime | None
    rfc: str | None
    cellphone: int | None
    typeUser: int

class PrivateUser(User):
    pw: str


"""
Códigos y seguridad
"""

# Instancia de autenticación
# Al tener el login en "/auth/login", tokenUrl debe ser "auth/login"
oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login")

# Algoritmo
ALGORITHM = os.getenv("ALGORITHM")

# Contexto de cifrado
crypt = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Duración del token (en minutos)
ACCESS_TOKEN_DURATION = int(os.getenv("ACCESS_TOKEN_DURATION", 30))

# Secreto para codificar y decodificar el JWT
SECRET = os.getenv("SECRET")


"""
Proceso de autenticación
"""

# Consulta para obtener el usuario por username (usado en login)
search_user_by_username_query = """
    SELECT * FROM users WHERE username = ?
"""

# Consulta para obtener el usuario por Id (usado para verificar el token)
search_user_by_id_query = """
    SELECT * FROM users WHERE id = ?
"""

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

def _auth_is_configured() -> bool:
    return bool(SECRET and ALGORITHM)

def search_private_user(username: str) -> PrivateUser | None:
    try:
        database = Database()
        rows = database.fetch_query(search_user_by_username_query, (username,))
        if not rows:
            return None
        user_db = rows[0]
        return PrivateUser(
            id=user_db["id"],
            username=user_db["username"],
            fullname=user_db["fullname"],
            birthday=_parse_birthday(user_db.get("birthday")),
            rfc=user_db.get("rfc"),
            cellphone=user_db.get("cellphone"),
            pw=user_db["password"],
            typeUser=user_db["user_type"],
        )
    except Exception as e:
        print(f"Error in search_private_user: {e}")
        return None

def search_user(user_id: int) -> User | None:
    try:
        database = Database()
        rows = database.fetch_query(search_user_by_id_query, (user_id,))
        if not rows:
            return None
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
    except Exception as e:
        print(f"Error in search_user: {e}")
        return None

invalid_token_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid token",
    headers={"WWW-Authenticate": "Bearer"},
)

async def auth_user(token: str = Depends(oauth2)) -> User:
    if not _auth_is_configured():
        raise HTTPException(status_code=500, detail="Auth is not configured (SECRET/ALGORITHM)")

    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise invalid_token_exception
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise invalid_token_exception

    user = search_user(user_id)
    if user is None:
        raise invalid_token_exception
    return user

def current_user(user: User = Depends(auth_user)) -> User:
    return user






"""
Todos los endpoints
"""

# Función de testeo
@router_authentication.get("/ison")
async def ison():
    return {
        "message" : "Yes, I'm working!"
        }

@router_authentication.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    if not _auth_is_configured():
        raise HTTPException(status_code=500, detail="Auth is not configured (SECRET/ALGORITHM)")

    user = search_private_user(form.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or user does not exist",
        )

    if not crypt.verify(form.password, user.pw):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_DURATION)
    payload = {"sub": str(user.id), "exp": datetime.utcnow() + access_token_expires}
    encoded_jwt = jwt.encode(payload, SECRET, algorithm=ALGORITHM)

    return {
        "access_token": encoded_jwt,
        "token_type": "bearer",
        "dashboard": "/dashboard",
    }

@router_authentication.get("/me")
async def me(user: User = Depends(current_user)):
    return user

@router_authentication.get("/getUserInfo/{otherUser}")
async def get_user_info(
    otherUser: str,
    user: User = Depends(current_user),
):
    other = search_private_user(otherUser)
    if other is None:
        return None
    return User(
        id=other.id,
        username=other.username,
        fullname=other.fullname,
        birthday=other.birthday,
        rfc=other.rfc,
        cellphone=other.cellphone,
    )
