# Writara

Herramienta de escritura y conocimiento construida con Django.

## Instalación

```bash
pip install django html2text bleach
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Cuenta de demo

- Usuario: `demo`  
- Contraseña: `demo1234`

## Features implementadas

- ✅ Editor rico con Quill (H1–H3, bold, italic, listas, citas, código)
- ✅ Autoguardado con debounce + intervalo configurable
- ✅ Historial de versiones (snapshot automático)
- ✅ Exportación: Markdown, HTML, Texto plano
- ✅ Modo enfoque (Ctrl+Shift+F)
- ✅ Pomodoro timer integrado
- ✅ Estadísticas en vivo (palabras, caracteres, lectura)
- ✅ Índice de encabezados automático
- ✅ Notas con wiki links `[[nombre]]`
- ✅ Backlinks y enlaces salientes
- ✅ Grafo de conocimiento (D3.js)
- ✅ Tags en notas
- ✅ Quick capture (botón +, Ctrl+Shift+N)
- ✅ Proyectos con secciones, personajes, lugares
- ✅ Tablero kanban de tareas
- ✅ Análisis textual (densidad léxica, voz pasiva, top palabras)
- ✅ Búsqueda global (documentos + notas + proyectos)
- ✅ Command Palette (Ctrl+K)
- ✅ Tema oscuro/claro
- ✅ Preferencias de usuario (fuente, ancho, autosave)
- ✅ Diseño editorial dark-first

## Estructura

```
main/
├── apps/
│   ├── accounts/   — usuarios y preferencias
│   ├── editor/     — documentos y editor rico
│   ├── notes/      — notas con wiki links y grafo
│   ├── projects/   — proyectos narrativos
│   ├── analysis/   — análisis textual
│   └── search/     — búsqueda global + command palette
├── static/css/     — writara.css (sistema de diseño)
└── templates/      — plantillas Django
```
