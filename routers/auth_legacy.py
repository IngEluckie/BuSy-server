"""
Módulo de inicio de sesión y verificación de usuarios
"""

# Importamos librerías
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from pydantic import BaseModel

# Importamos la clase para la base de datos
from database.singleton import Database

# Iniciar router
router_authentication = APIRouter(prefix="/auth")

# Cargar variables de entorno
load_dotenv()

# Función de testeo
@router_authentication.get("/ison")
async def ison():
    return {"message": "Yeah ma'afaka im on!"}


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
Clases modelo para usuarios:
- User: datos públicos
- UserPrivate: incluye la contraseña y tipo de usuario
"""

class User(BaseModel):
    user_iD: int
    username: str
    name: str
    email: str

class UserPrivate(User):
    password: str
    typeUser: int


"""
Proceso de autenticación
"""

# Consulta para obtener el usuario por username (usado en login)
search_user_by_username_query = """
    SELECT * FROM Usuarios WHERE username = ?
"""

# Consulta para obtener el usuario por Id (usado para verificar el token)
search_user_by_id_query = """
    SELECT * FROM Usuarios WHERE Id_Usuarios = ?
"""

def search_user_private(username: str):
    try:
        database = Database()
        user_db_list = database.fetch_query(search_user_by_username_query, (username,))
        if not user_db_list:
            return None
        user_db = user_db_list[0]
        return UserPrivate(
            user_iD=user_db["Id_Usuarios"],
            username=user_db["username"],
            name=user_db["NombreCompleto"],
            email=user_db["email"],
            password=user_db["Password"],
            typeUser=user_db["Tipo_usuario"]
        )
    except Exception as e:
        print(f"Error en search_user_private: {e}")
        return None

def search_user(user_iD: int):
    try:
        database = Database()
        user_db_list = database.fetch_query(search_user_by_id_query, (user_iD,))
        if not user_db_list:
            return None
        user_db = user_db_list[0]
        return User(
            user_iD=user_db["Id_Usuarios"],
            username=user_db["username"],
            name=user_db["NombreCompleto"],
            email=user_db["email"]
        )
    except Exception as e:
        print(f"Error en search_user: {e}")
        return None

invalid_token_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid token",
    headers={"WWW-Authenticate": "Bearer"},
)

async def auth_user(token: str = Depends(oauth2)):
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        print("Payload decodificado:", payload)  # Depuración
        user_iD_str = payload.get("sub")
        if user_iD_str is None:
            print("No se encontró 'sub' en el token")
            raise invalid_token_exception
        user_iD = int(user_iD_str)  # Convertir a entero
    except JWTError as e:
        print("Error al decodificar token:", e)
        raise invalid_token_exception
    
    user = search_user(user_iD)
    if user is None:
        print("Usuario no encontrado en la base de datos")
        raise invalid_token_exception
    return user

def current_user(user: User = Depends(auth_user)):
    return user

@router_authentication.post("/login")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    # Se busca el usuario por username (que es de tipo string)
    user = search_user_private(form.username)
    if not user:
        print("Error: Usuario no encontrado")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or user does not exist"
        )
    
    # Verificamos la contraseña (asumiendo que está encriptada con bcrypt)
    if not crypt.verify(form.password, user.password):
        print("Error: Contraseña incorrecta")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Generamos el token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_DURATION)
    payload = {
        "sub": str(user.user_iD),
        "exp": datetime.utcnow() + access_token_expires
    }
    encoded_jwt = jwt.encode(payload, SECRET, algorithm=ALGORITHM)

    return {
        "access_token": encoded_jwt,
        "token_type": "bearer",
        "dashboard": "/dashboard.html"
    }

@router_authentication.get("/me")
async def me(user: User = Depends(current_user)):
    return user

@router_authentication.get("/getUserInfo/{otherUser}")
async def getUserInfo(
    user: User = Depends(current_user),
    otherUser: str = ""
):
    try:
        db = Database()
        db_user = db.fetch_query(search_user_by_username_query, (otherUser,))
        if not db_user:
            return None
        userInfo = db_user[0]
        return User(
            user_iD=userInfo["Id_Usuarios"],
            username=userInfo["username"],
            name=userInfo["NombreCompleto"],
            email=userInfo["email"],
        )
    except Exception as e:
        raise Exception

