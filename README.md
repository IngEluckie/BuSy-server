# BuSy Docker Setup

Configuracion base para ejecutar BuSy en Docker durante desarrollo local.

## Requisitos

- Docker
- Docker Compose
- Archivo `.env` en la raiz del proyecto

Variables usadas actualmente por la aplicacion:

- `SECRET`
- `ALGORITHM`
- `ACCESS_TOKEN_DURATION`

## Comandos

Construir e iniciar el entorno:

```bash
docker compose up --build
```

Levantar el entorno sin reconstruir:

```bash
docker compose up
```

Detenerlo:

```bash
docker compose down
```

Reconstruir la imagen desde cero:

```bash
docker compose build --no-cache
```

## Persistencia y hot-reload

La aplicacion arranca con `uvicorn --reload`, por lo que los cambios en el codigo se reflejan durante desarrollo local.

Los siguientes directorios se montan desde el host al contenedor:

- `./main.py` hacia `/app/main.py`
- `./routers` hacia `/app/routers`
- `./utilities` hacia `/app/utilities`
- `./databases` hacia `/app/databases`
- `./static` hacia `/app/static`

Esto implica que:

- la base SQLite sigue viviendo en `databases/systemDB.db`
- los logs CSV siguen viviendo en `static/private/systemLogs`
- los archivos estaticos siguen siendo servidos desde `static/public`

Al recrear el contenedor, esos datos se conservan porque permanecen en tu directorio de trabajo local.

## Alcance de esta fase

Esta configuracion:

- estandariza el runtime local
- no cambia endpoints ni arquitectura interna
- mantiene scheduler y API en el mismo contenedor
- no migra la base de datos a otro motor
- no endurece el entorno para produccion
