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

## Publicacion en Docker Hub

La imagen de este proyecto puede publicarse en Docker Hub a partir del [`Dockerfile`](/Users/josueernestogalindomorales/Desktop/systems/dev/BuSy/Dockerfile:1).

Antes de la primera publicacion:

1. Crear un repositorio en Docker Hub, por ejemplo `eluckie/busy-server`.
2. Iniciar sesion desde terminal:

```bash
docker login
```

Construir la imagen y publicarla por primera vez:

```bash
docker build -t eluckie/busy-server:latest .
docker push eluckie/busy-server:latest
```

Si se quiere mantener una version fija y la etiqueta `latest` al mismo tiempo:

```bash
docker build -t eluckie/busy-server:1.0.0 -t eluckie/busy-server:latest .
docker push eluckie/busy-server:1.0.0
docker push eluckie/busy-server:latest
```

## Actualizacion de la imagen en Docker Hub

Cada vez que cambie el codigo y se quiera actualizar la imagen publicada, es necesario reconstruirla y volver a subir la etiqueta correspondiente.

Actualizar solo `latest`:

```bash
docker build -t eluckie/busy-server:latest .
docker push eluckie/busy-server:latest
```

Actualizar una version concreta y tambien `latest`:

```bash
docker build -t eluckie/busy-server:1.0.1 -t eluckie/busy-server:latest .
docker push eluckie/busy-server:1.0.1
docker push eluckie/busy-server:latest
```

Si ya existe una sesion activa en Docker Hub, no es necesario repetir `docker login` en cada actualizacion.

Para usar la imagen publicada desde Docker Compose, el servicio puede referenciarla con `image:`:

```yaml
services:
  app:
    image: eluckie/busy-server:latest
    ports:
      - "8000:8000"
    env_file:
      - .env
```

## Persistencia y hot-reload

La aplicacion arranca con `uvicorn --reload`, por lo que los cambios en el codigo se reflejan durante desarrollo local.

Los siguientes mounts se usan desde el host al contenedor:

- `./` hacia `/workspace` para persistir `.busy.zip`
- `./main.py` hacia `/app/main.py`
- `./routers` hacia `/app/routers`
- `./utilities` hacia `/app/utilities`
- `./databases` hacia `/app/databases`
- `./static` hacia `/app/static`

Esto implica que:

- el artefacto persistente principal es `.busy.zip`
- el runtime activo se descomprime temporalmente dentro del contenedor en `BUSY_RUNTIME_DIR`
- la base SQLite activa vive temporalmente en `BUSY_RUNTIME_DIR/db/main.sqlite3`
- los logs CSV activos viven temporalmente en `BUSY_RUNTIME_DIR/logs`
- si el ZIP no existe, el sistema crea `.busy.zip` con la estructura inicial y luego genera la base dentro del runtime
- los archivos estaticos siguen siendo servidos desde `static/public`

Al recrear el contenedor, los datos se conservan porque `.busy.zip` permanece en tu directorio de trabajo local.

## Alcance de esta fase

Esta configuracion:

- estandariza el runtime local
- no cambia endpoints ni arquitectura interna
- mantiene scheduler y API en el mismo contenedor
- no migra la base de datos a otro motor
- no endurece el entorno para produccion
