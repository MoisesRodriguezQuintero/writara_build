# Writara

**Escritura, notas y proyectos en un solo lugar.** Un editor por páginas, proyectos narrativos con biblia y línea temporal, y notas enlazadas con grafo que viven dentro de cada proyecto. Auto-hospedable, multiusuario y sin dependencias de servicios externos para funcionar.

`v1.1.0` · Django 6 · PostgreSQL / SQLite · [Licencia de evaluación](LICENSE)

> Writara es **código disponible (source-available)**, no código abierto: puedes leerlo y evaluarlo, pero su uso comercial, en producción o la redistribución requieren permiso. Consulta la sección [Licencia](#licencia).

---

## Funciones

**Escritura**
- Editor de texto enriquecido (Quill) con autoguardado, historial de versiones, modo enfoque y Pomodoro.
- **Edición por páginas**: elige A3, A4, **A5 (por defecto)**, A6, B5, Carta o Legal; el texto se reparte en hojas con indicador «Página X / N».
- Exportación a **PDF, ODT y HTML paginados** (con el tamaño de página del documento y número de página), Markdown y texto plano.
- Análisis textual: densidad léxica, longitud de frases, voz pasiva, palabras frecuentes.

**Proyectos**
- Estructura en secciones, biblia (personajes y lugares), línea temporal y tareas en kanban.
- **Notas dentro de cada proyecto**: pestaña propia, bandeja de entrada, enlaces `[[nombre de nota]]` con *backlinks*, etiquetas y grafo de conocimiento por proyecto.
- «Notas generales»: un proyecto especial por usuario para ideas sueltas y capturas rápidas.

**Interfaz**
- Captura rápida (+) que guarda en el proyecto que tienes abierto, paleta de comandos (Ctrl+K), búsqueda global y tema oscuro/claro.
- Multiusuario: cada persona ve solo lo suyo.

## Cómo se organiza

| Concepto | Qué es |
|---|---|
| **Documento** | Un texto independiente con su tamaño de página. |
| **Proyecto** | Agrupa secciones, personajes, lugares, línea temporal, tareas y **notas**. |
| **Nota** | Texto plano que pertenece a un proyecto. Los enlaces `[[…]]` solo conectan notas **del mismo proyecto**, y una nota se puede mover a otro desde el editor. |

---

## Arranque rápido (Docker)

Requisitos: Docker y Docker Compose.

```bash
git clone <url-del-repositorio> writara
cd writara
cp .env.example .env        # edita SECRET_KEY y la contraseña de PostgreSQL
docker compose up --build
```

La aplicación queda en `http://localhost:8000`. Aplica las migraciones y recoge los estáticos automáticamente. Crea el primer usuario en `/accounts/register/` o con:

```bash
docker compose exec web python manage.py createsuperuser
```

### Comandos útiles

```bash
docker compose up -d                                   # en segundo plano
docker compose logs -f web                             # logs
docker compose down                                    # parar
docker compose down -v                                 # parar y borrar la base de datos
docker compose exec web python manage.py migrate       # migraciones manuales
docker compose exec db psql -U writara -d writara      # consola de PostgreSQL
```

### Acceso desde la red local

Añade tu IP a `ALLOWED_HOSTS` en `.env` (por ejemplo `localhost,127.0.0.1,192.168.1.20`) y reinicia con `docker compose down && docker compose up -d`.

## Desarrollo local (sin Docker)

```bash
python -m venv .venv
source .venv/bin/activate          # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate           # sin POSTGRES_HOST usa SQLite automáticamente
python manage.py runserver
```

La exportación a PDF necesita las librerías del sistema de [WeasyPrint](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) (Pango y Cairo); en la imagen Docker ya vienen incluidas.

## Configuración

Copia `.env.example` a `.env`.

| Variable | Descripción | Ejemplo |
|---|---|---|
| `SECRET_KEY` | Clave secreta de Django. **Obligatoria con `DEBUG=False`.** | cadena aleatoria de 50+ caracteres |
| `DEBUG` | Modo depuración | `False` en producción |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por comas | `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | Orígenes https de confianza (tras proxy o dominio propio) | `https://writara.example.com` |
| `POSTGRES_DB` · `POSTGRES_USER` · `POSTGRES_PASSWORD` | Base de datos PostgreSQL | `writara` |
| `POSTGRES_HOST` · `POSTGRES_PORT` | Si no hay `POSTGRES_HOST`, se usa SQLite | `db` · `5432` |
| `WEB_PORT` | Puerto expuesto por Docker | `8000` |

## Actualizar desde una versión anterior

1. Actualiza el código y `pip install -r requirements.txt`.
2. `python manage.py migrate`.
3. **Reinicia el servidor** (con `DEBUG=False` Django mantiene las plantillas en memoria). Con Docker, reconstruye: `docker compose up -d --build`.

**De 1.0.x a 1.1.0:** todas tus notas existentes se mueven al proyecto «Notas generales» de su dueño (los enlaces y el grafo siguen igual) y puedes moverlas a otro proyecto desde el editor. La entrada «Notas» de la barra lateral desaparece: ahora las notas están en la pestaña **Notas** de cada proyecto.

## Estructura del código

```
main/
├── apps/
│   ├── accounts/   usuarios y preferencias
│   ├── editor/     documentos, versiones, páginas y exportación (PDF, ODT, HTML, Markdown, texto)
│   ├── projects/   proyectos, estructura, biblia, línea temporal y tareas
│   ├── notes/      notas de proyecto, enlaces [[ ]], etiquetas y grafo
│   ├── analysis/   análisis de texto
│   └── search/     búsqueda global y paleta de comandos
├── static/         CSS y JavaScript propio (paginación)
└── templates/
tests_js/           pruebas de JavaScript (Node)
```

## Tests

```bash
python manage.py test main
node tests_js/pagination.test.js
```

La suite cubre saneado de HTML, exportadores, notas y proyectos, migraciones, análisis de texto y, si [Playwright](https://playwright.dev/python/) está instalado, el guardado de notas y las pestañas del proyecto en un navegador real (se omiten solas si no lo está).

## Pila tecnológica

Django 6 · PostgreSQL 16 / SQLite · Gunicorn · WhiteNoise · WeasyPrint · Alpine.js, Quill y D3.js (por CDN). Las licencias de los componentes de terceros están en [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

---

## Licencia

Writara se distribuye bajo la [Licencia de Evaluación de Writara](LICENSE) (versión 1.0): puedes **leer el código y probarlo** con fines personales, educativos o de evaluación interna —incluida la revisión previa a una licencia o adquisición—. El uso comercial o en producción, la redistribución y los trabajos derivados publicados requieren permiso escrito.

Para una licencia comercial o para hablar de la adquisición del proyecto, escribe a **[CORREO DE CONTACTO]**.

Las versiones publicadas antes de la 1.1.0 pudieron distribuirse con otras condiciones; esas copias se rigen por los términos con los que se obtuvieron.
