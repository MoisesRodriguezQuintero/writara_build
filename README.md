# Writara

Herramienta de escritura y conocimiento personal. Editor rico, notas con wiki links, grafo de conocimiento, proyectos narrativos con biblia y línea temporal, análisis textual y búsqueda global.

Construido con Django + PostgreSQL. Auto-hosteable, open source.

---

## Arranque rápido

### Requisitos

- Docker
- docker-compose

### Instalación

```bash
git clone https://github.com/tu-usuario/writara.git
cd writara
cp .env.example .env
```

Edita `.env` con tus valores:

```bash
nano .env
```

```bash
docker-compose up --build
```

La primera vez aplica las migraciones automáticamente. La aplicación estará disponible en `http://localhost:8000`.

### Crear el primer usuario

```bash
docker-compose exec web python manage.py createsuperuser
```

O registrarse directamente en `/accounts/register/`.

---

## Acceso en red local

Para que otros usuarios en la misma red puedan conectarse:

1. Encuentra tu IP local:
   ```bash
   hostname -I
   ```

2. Añade tu IP a `ALLOWED_HOSTS` en `.env`:
   ```
   ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.XX
   ```

3. Reinicia:
   ```bash
   docker-compose down && docker-compose up -d
   ```

4. Tus compañeros acceden en `http://192.168.1.XX:8000`

---

## Comandos útiles

```bash
# Levantar en segundo plano
docker-compose up -d

# Ver logs
docker-compose logs -f web

# Parar
docker-compose down

# Parar y borrar volúmenes (borra la base de datos)
docker-compose down -v

# Aplicar migraciones manualmente
docker-compose exec web python manage.py migrate

# Abrir shell de Django
docker-compose exec web python manage.py shell

# Acceder a la base de datos
docker-compose exec db psql -U writara -d writara
```

---

## Variables de entorno

Copia `.env.example` a `.env` y rellena los valores.

| Variable | Descripción | Ejemplo |
|---|---|---|
| `SECRET_KEY` | Clave secreta de Django | cadena aleatoria de 50+ chars |
| `DEBUG` | Modo debug | `False` en producción |
| `ALLOWED_HOSTS` | Hosts permitidos | `localhost,127.0.0.1,192.168.1.10` |
| `POSTGRES_DB` | Nombre de la base de datos | `writara` |
| `POSTGRES_USER` | Usuario de PostgreSQL | `writara` |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL | cadena segura |
| `WEB_PORT` | Puerto expuesto | `8000` |

---

## Desarrollo local sin Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Sin definir POSTGRES_HOST, usa SQLite automáticamente
python manage.py migrate
python manage.py runserver
```

---

## Imagen en Docker Hub

```bash
docker pull moisesrodriguezquintero/writara:latest
```

Para usar la imagen publicada en lugar de construir localmente, cambia en `docker-compose.yml`:

```yaml
web:
  image: moisesrodriguezquintero/writara:latest
  # build: .   ← comentar esta línea
```

---

## Stack

- **Backend**: Django 6
- **Base de datos**: PostgreSQL 16
- **Servidor**: Gunicorn
- **Estáticos**: Whitenoise
- **Frontend**: Alpine.js, Quill, D3.js (CDN)
- **Contenedores**: Docker + docker-compose

---

## Features

- Editor rico (Quill) con autoguardado, historial de versiones, modo enfoque, Pomodoro
- Exportación a Markdown, HTML, ODT, texto plano
- Notas con wiki links `[[nombre]]`, backlinks, tags
- Grafo de conocimiento interactivo (D3.js)
- Quick capture global (Ctrl+Shift+N)
- Proyectos narrativos: estructura, biblia (personajes y lugares), línea temporal, tareas kanban
- Análisis textual: densidad léxica, voz pasiva, palabras frecuentes
- Búsqueda global en documentos, notas y proyectos
- Command Palette (Ctrl+K)
- Tema oscuro / claro
- Multiusuario con PostgreSQL

---

## Licencia

MIT