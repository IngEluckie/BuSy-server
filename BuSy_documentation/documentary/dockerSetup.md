# Docker Setup

## Objetivo

Estandarizar el entorno de ejecucion local de BuSy usando Docker, sin cambiar la arquitectura actual del proyecto.

La configuracion actual:

- usa FastAPI con `uvicorn`
- mantiene SQLite como base de datos local
- conserva logs CSV en archivos del proyecto
- usa `.busy` como persistencia principal y un runtime temporal fuera del repo
- deja scheduler y API en el mismo contenedor

## Archivos involucrados

- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `requirements.txt`

## Flujo normal de uso

### Construir y levantar el entorno

```bash
docker compose up --build
```

Este comando:

- construye la imagen
- instala dependencias
- levanta el contenedor
- expone la app en el puerto `8000`

### Levantar sin reconstruir

```bash
docker compose up
```

### Apagar el entorno

```bash
docker compose down
```

### Reconstruir completamente la imagen

```bash
docker compose build --no-cache
docker compose up
```

## Verificacion basica

Una vez levantado el entorno, probar:

```bash
curl http://localhost:8000/ison
```

La respuesta esperada debe indicar que el servidor esta funcionando.

## Logs

Ver logs del contenedor:

```bash
docker compose logs
```

Seguir logs en vivo:

```bash
docker compose logs -f
```

## Que revisar despues de levantarlo

- que el archivo `.env` tenga las variables necesarias
- que `/ison` responda correctamente
- que el login siga funcionando
- que `.busy` exista o se regenere
- que los archivos de log sigan actualizandose dentro del runtime temporal

## Persistencia y desarrollo local

La configuracion de Docker monta directorios del proyecto desde el host al contenedor. Eso permite:

- hot-reload durante desarrollo
- persistencia de la base SQLite
- persistencia de los logs CSV

Los datos persistidos viven en el proyecto local dentro de:

- `.busy`

Durante la ejecucion, BuSy descomprime el contenedor en `BUSY_RUNTIME_DIR`, opera sobre archivos normales y vuelve a compactar el resultado en `.busy`.

## Variables de entorno

La aplicacion carga configuracion desde `.env`.

Variables usadas actualmente:

- `SECRET`
- `ALGORITHM`
- `ACCESS_TOKEN_DURATION`
- `BUSY_ARCHIVE_PATH`
- `BUSY_RUNTIME_DIR`

## Flujo recomendado

1. Ejecutar `docker compose up --build`
2. Probar endpoints y autenticacion
3. Desarrollar normalmente con hot-reload
4. Apagar con `docker compose down`
