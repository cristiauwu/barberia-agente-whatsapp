# n8n + Postgres — servicio de Docker Desktop

La forma más simple es desde **Docker Desktop**, que ya tienes instalado y
funcionando.

## Arrancar / detener

Desde Docker Desktop → pestaña **Containers**: verás `barberia-n8n` y
`barberia-postgres`, con botones de play y stop.

O desde una terminal (PowerShell):

```powershell
# El CLI de Docker vive en tu carpeta de usuario, no en Program Files
$docker = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"

# Arrancar
& $docker compose up -d

# Ver el estado
& $docker compose ps

# Ver los registros en vivo
& $docker compose logs -f n8n

# Detener (conserva tus datos)
& $docker compose down

# ⚠️ Borra TODO, incluidos workflows y la base de datos
& $docker compose down -v
```

> **Si `docker` no funciona en tu terminal**, es porque el `PATH` no incluye la
> carpeta del CLI y además falta el ayudante de credenciales. En ese caso usa
> `docker-helper.py` (ver abajo) o abre el proyecto desde Docker Desktop.

## Abrir n8n

Una vez arrancado, entra a:

**http://localhost:5678**

La primera vez te pedirá crear la cuenta de propietario (correo y contraseña).
Es local: esa contraseña no sale de tu equipo.

## Atajo con el helper

`docker-helper.py` evita los problemas de comillas de PowerShell con Docker:

```powershell
$uv = "$env:LOCALAPPDATA\..\.cherrystudio\bin\uv.exe"   # o donde tengas uv

uv run python docker-helper.py ps            # estado de los contenedores
uv run python docker-helper.py logs n8n      # registros
uv run python docker-helper.py mcp-status    # estado del servidor MCP
```

## Qué contiene

| Contenedor | Para qué | Puerto |
| --- | --- | --- |
| `barberia-n8n` | n8n 2.40.6 | 5678 |
| `barberia-postgres` | Base de datos y memoria del agente | interno |

Los datos viven en volúmenes de Docker (`barberia_n8n_data`,
`barberia_postgres_data`), así que sobreviven a reinicios y a `docker compose down`.
Solo `down -v` los borra.

## Seguridad

- `.env` tiene la contraseña de Postgres y la clave de cifrado de n8n.
  **No lo compartas ni lo subas a un repositorio.**
- La llave de Uncensored AI **no está en ningún archivo**: se pega en la
  interfaz de n8n, en *Credentials*.
- Este stack escucha solo en `localhost`, no está expuesto a internet.