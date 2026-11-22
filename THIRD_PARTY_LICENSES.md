# Licencias de terceros

Writara se distribuye bajo la [licencia de Writara](LICENSE). Esa licencia **solo cubre el código propio** del proyecto. Los componentes de esta lista pertenecen a sus autores y se rigen por sus propias licencias, que no se modifican.

Última revisión: 22 de noviembre de 2026 (Writara 1.1.0).

**Cómo leer la columna «Verificación»:**
- **Verificada**: licencia leída en los metadatos del paquete instalado en el entorno del proyecto.
- **Pendiente**: licencia indicada según la documentación pública del proyecto; confirmar con `pip-licenses` (ver al final) antes de una auditoría o venta.

## Dependencias de Python

Directas (las de `requirements.txt`):

| Componente | Versión revisada | Licencia | Para qué se usa | Verificación |
|---|---|---|---|---|
| [Django](https://www.djangoproject.com/) | 6.0.5 | BSD-3-Clause | Framework web | Verificada |
| [bleach](https://github.com/mozilla/bleach) | 6.3.0 | Apache-2.0 | Saneado del HTML de usuario | Verificada |
| [odfpy](https://github.com/eea/odfpy) | 1.4.1 | Apache-2.0 **o** GPL (doble licencia) | Exportación a ODT | Verificada |
| [WeasyPrint](https://weasyprint.org/) | — | BSD-3-Clause | Exportación a PDF | Pendiente |
| [gunicorn](https://gunicorn.org/) | — | MIT | Servidor de aplicación (producción) | Pendiente |
| [WhiteNoise](https://github.com/evansd/whitenoise) | — | MIT | Archivos estáticos (producción) | Pendiente |
| [psycopg2](https://www.psycopg.org/) | — | LGPL-3.0-or-later (con excepción OpenSSL) | Conexión a PostgreSQL | Pendiente |

Indirectas (las instala alguna de las anteriores):

| Componente | Versión revisada | Licencia | Verificación |
|---|---|---|---|
| [asgiref](https://github.com/django/asgiref) | 3.11.1 | BSD-3-Clause | Verificada |
| [sqlparse](https://github.com/andialbrecht/sqlparse) | 0.5.5 | BSD-3-Clause | Verificada |
| [webencodings](https://github.com/gsnedders/python-webencodings) | 0.5.1 | BSD-3-Clause | Verificada |
| [defusedxml](https://github.com/tiran/defusedxml) | 0.7.1 | PSF-2.0 | Verificada |

WeasyPrint instala además otras dependencias (por ejemplo `tinycss2`, `cssselect2`, `Pyphen`, `fontTools`, `Pillow`); no se han revisado aquí.

## Recursos del navegador (cargados desde CDN, no incluidos en el repositorio)

| Componente | Versión | Licencia | Para qué se usa |
|---|---|---|---|
| [Alpine.js](https://alpinejs.dev/) | 3.13.5 | MIT | Interactividad de la interfaz |
| [Quill](https://quilljs.com/) | 1.3.7 | BSD-3-Clause | Editor de texto enriquecido |
| [D3](https://d3js.org/) | 7.x | ISC | Grafo de notas |
| [Lora](https://fonts.google.com/specimen/Lora) | — | SIL OFL 1.1 | Tipografía del texto (Google Fonts) |
| [DM Sans](https://fonts.google.com/specimen/DM+Sans) | — | SIL OFL 1.1 | Tipografía de la interfaz (Google Fonts) |
| [JetBrains Mono](https://www.jetbrains.com/lp/mono/) | — | SIL OFL 1.1 | Tipografía monoespaciada (Google Fonts) |

Las fuentes se piden a Google Fonts desde el navegador del usuario; no se redistribuyen con Writara.

## Librerías del sistema (imagen Docker)

La exportación a PDF necesita librerías instaladas con `apt` en la imagen: Pango, Cairo y gdk-pixbuf (licencias LGPL/MPL) y `libpq` (PostgreSQL License). Se usan como librerías compartidas, sin modificarlas.

## Solo desarrollo y pruebas (no forman parte de la aplicación)

| Componente | Licencia | Uso |
|---|---|---|
| [Playwright](https://playwright.dev/python/) | Apache-2.0 | Pruebas opcionales en navegador real |
| [Node.js](https://nodejs.org/) | MIT | Pruebas de JavaScript |

## Notas de cumplimiento

1. **Sin dependencias de copyleft fuerte.** Hasta la 1.0.x la exportación a Markdown usaba `html2text` (GPL-3.0). Desde la 1.1.0 usa un conversor propio (`main/apps/editor/markdown.py`) y esa dependencia se ha eliminado.
2. **`odfpy` (doble licencia).** Se utiliza bajo los términos de **Apache-2.0**.
3. **`psycopg2` (LGPL).** Se usa como librería sin modificar. Si se modificara, habría que publicar esos cambios.
4. **`bleach` está en mantenimiento limitado**: Mozilla anunció su obsolescencia en 2023. Sigue funcionando, pero un comprador podría preguntar por su futuro; `nh3` es la alternativa que se suele recomendar.
5. **Licencias permisivas (BSD, MIT, ISC, PSF, Apache).** Al redistribuir el software hay que conservar sus avisos de copyright y el texto de la licencia. Apache-2.0 exige además conservar los ficheros `NOTICE`, si los hay.

## Cómo regenerar o auditar esta lista

```bash
pip install pip-licenses
pip-licenses --format=markdown --with-urls --with-system
```

Compara el resultado con las tablas anteriores y actualiza las filas marcadas como «Pendiente». Revisa también las dependencias de WeasyPrint.

> Nota: `odfpy` se publica con doble licencia (Apache-2.0 o GPL); Writara la usa bajo Apache-2.0.
