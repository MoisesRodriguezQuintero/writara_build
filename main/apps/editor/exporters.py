from functools import lru_cache
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path

from django.template.loader import render_to_string

from main.utils import clean_html, html_to_text
from .pagesizes import get_page, mm

PAGINATION_JS = Path(__file__).resolve().parents[2] / 'static' / 'js' / 'pagination.js'
PX_TO_MM = 25.4 / 96


@lru_cache(maxsize=1)
def _pagination_js():
    return PAGINATION_JS.read_text(encoding='utf-8')


def _blocked_url_fetcher(url, *args, **kwargs):
    """WeasyPrint solo puede cargar recursos incrustados (data:). Bloquea http(s)
    y file:// para que un documento no pueda leer ficheros locales ni hacer
    peticiones de red desde el servidor al generar el PDF."""
    from weasyprint import default_url_fetcher
    if url.startswith('data:'):
        return default_url_fetcher(url, *args, **kwargs)
    raise ValueError(f'Recurso externo bloqueado: {url}')


class DocumentExporter:
    def __init__(self, doc, prefs=None):
        self.doc = doc
        # Todo el HTML de usuario se sanea antes de exportarlo
        self.content = clean_html(doc.content)
        # Página y tipografía: las mismas que ve el usuario en el editor
        self.page = get_page(doc.page_size)
        self.font_px = getattr(prefs, 'editor_font_size', None) or 17
        self.spacing_px = getattr(prefs, 'paragraph_spacing', None)
        self.spacing_px = 10 if self.spacing_px is None else self.spacing_px
        self.indent_px = getattr(prefs, 'text_indent', None) or 0

    def to_html(self):
        page = self.page
        return render_to_string('editor/export.html', {
            'doc': self.doc,
            # Texto ya formateado: la localización (es) pondría coma decimal en el CSS
            'page': {'key': page['key'], 'label': page['label'],
                     'w_mm': mm(page['w']), 'h_mm': mm(page['h']),
                     'margin_mm': mm(page['margin'])},
            'page_geometry': {'w': page['w'], 'h': page['h'], 'margin': page['margin']},
            'font_px': self.font_px,
            'spacing_px': self.spacing_px,
            'indent_px': self.indent_px,
            'pagination_js': _pagination_js(),
        })

    def to_markdown(self):
        try:
            import html2text
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.body_width = 0
            return f"# {self.doc.title}\n\n" + h.handle(self.content)
        except ImportError:
            return f"# {self.doc.title}\n\n{html_to_text(self.content).strip()}"

    def to_text(self):
        return html_to_text(self.content).strip() + '\n'

    def to_pdf(self):
        from weasyprint import HTML as WeasyprintHTML
        return WeasyprintHTML(
            string=self.to_html(), url_fetcher=_blocked_url_fetcher
        ).write_pdf()

    def to_odt(self) -> bytes:
        from odf.opendocument import OpenDocumentText
        from odf.style import (
            Style, TextProperties, ParagraphProperties, PageLayout,
            PageLayoutProperties, MasterPage, Footer, FooterStyle,
            HeaderFooterProperties,
        )
        from odf.text import H, P, Span, LineBreak, PageNumber

        doc_odt = OpenDocumentText()

        # ── Página: tamaño, márgenes y número de página en el pie ────────────
        page = self.page
        footer_mm = 6   # el pie ocupa parte del margen inferior (el área útil no cambia)
        layout = PageLayout(name="PageLayout1")
        layout.addElement(PageLayoutProperties(
            pagewidth=f"{mm(page['w'])}mm", pageheight=f"{mm(page['h'])}mm",
            printorientation="portrait",
            margintop=f"{mm(page['margin'])}mm",
            marginbottom=f"{mm(page['margin'] - footer_mm)}mm",
            marginleft=f"{mm(page['margin'])}mm", marginright=f"{mm(page['margin'])}mm",
        ))
        footer_style = FooterStyle()
        footer_style.addElement(HeaderFooterProperties(minheight=f"{footer_mm}mm", margintop="0mm"))
        layout.addElement(footer_style)
        doc_odt.automaticstyles.addElement(layout)

        master = MasterPage(name="Standard", pagelayoutname=layout)
        footer = Footer()
        footer_p = P(stylename="Footer")
        footer_p.addElement(PageNumber(selectpage="current"))
        footer.addElement(footer_p)
        master.addElement(footer)
        doc_odt.masterstyles.addElement(master)

        footer_par = Style(name="Footer", family="paragraph")
        footer_par.addElement(ParagraphProperties(textalign="center"))
        footer_par.addElement(TextProperties(fontsize="9pt", color="#888888"))
        doc_odt.styles.addElement(footer_par)

        # ── Tipografía: la misma que en el editor ─────────────────────────────
        base_pt = self.font_px * 0.75
        spacing_mm = mm(round(self.spacing_px * PX_TO_MM, 2))
        indent_mm = mm(round(self.indent_px * PX_TO_MM, 2))

        for level, factor in ((1, 1.7), (2, 1.35), (3, 1.1)):
            style = Style(name=f"Heading{level}", family="paragraph")
            style.addElement(TextProperties(fontsize=f"{base_pt * factor:.1f}pt", fontweight="bold"))
            style.addElement(ParagraphProperties(
                margintop=f"{base_pt * factor * 0.35:.1f}pt", marginbottom="6pt", keepwithnext="always"))
            doc_odt.styles.addElement(style)

        body_style = Style(name="Body", family="paragraph")
        body_style.addElement(TextProperties(fontsize=f"{base_pt:.1f}pt"))
        body_style.addElement(ParagraphProperties(
            lineheight="185%", marginbottom=f"{spacing_mm}mm", textindent=f"{indent_mm}mm"))
        doc_odt.styles.addElement(body_style)

        quote_style = Style(name="Quote", family="paragraph")
        quote_style.addElement(TextProperties(fontsize=f"{base_pt:.1f}pt", fontstyle="italic"))
        quote_style.addElement(ParagraphProperties(
            marginleft="1cm", lineheight="185%", marginbottom=f"{spacing_mm}mm"))
        doc_odt.styles.addElement(quote_style)

        code_style = Style(name="Code", family="paragraph")
        code_style.addElement(TextProperties(fontsize=f"{base_pt * 0.85:.1f}pt", fontfamily="Courier New"))
        doc_odt.styles.addElement(code_style)

        list_style = Style(name="ListItem", family="paragraph")
        list_style.addElement(TextProperties(fontsize=f"{base_pt:.1f}pt"))
        list_style.addElement(ParagraphProperties(marginleft="0.8cm", lineheight="170%"))
        doc_odt.styles.addElement(list_style)

        title_p = H(outlinelevel=1, stylename="Heading1")
        title_p.addText(self.doc.title)
        doc_odt.text.addElement(title_p)

        class QuillParser(HTMLParser):
            INLINE = {
                'strong': 'bold', 'b': 'bold', 'em': 'italic', 'i': 'italic',
                'u': 'underline', 's': 'strike', 'strike': 'strike', 'del': 'strike',
            }
            BLOCKS = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'blockquote', 'pre')

            def __init__(self, odt_doc):
                super().__init__()
                self.odt = odt_doc
                self.current = None        # párrafo abierto
                self.block_tag = None
                self.inline = []           # pila de formatos en línea abiertos
                self.lists = []            # pila de listas: ['ul'] / ['ol', contador]
                self._inline_counter = 0

            # -- bloques --------------------------------------------------
            def _open(self, tag):
                self._close()
                self.block_tag = tag
                if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                    level = min(int(tag[1]), 3)
                    self.current = H(outlinelevel=level, stylename=f"Heading{level}")
                elif tag == 'blockquote':
                    self.current = P(stylename="Quote")
                elif tag == 'pre':
                    self.current = P(stylename="Code")
                elif tag == 'li':
                    self.current = P(stylename="ListItem")
                    if self.lists and self.lists[-1][0] == 'ol':
                        self.lists[-1][1] += 1
                        self.current.addText(f"{self.lists[-1][1]}. ")
                    else:
                        self.current.addText("• ")
                else:
                    self.current = P(stylename="Body")

            def _close(self):
                if self.current is not None:
                    self.odt.text.addElement(self.current)
                self.current = None
                self.block_tag = None

            def handle_starttag(self, tag, attrs):
                if tag in ('ul', 'ol'):
                    self._close()
                    self.lists.append([tag, 0])
                elif tag in self.BLOCKS:
                    self._open(tag)
                elif tag == 'br':
                    if self.current is not None:
                        self.current.addElement(LineBreak())
                elif tag in self.INLINE:
                    self.inline.append(self.INLINE[tag])

            def handle_endtag(self, tag):
                if tag in ('ul', 'ol'):
                    self._close()
                    if self.lists:
                        self.lists.pop()
                elif tag in self.BLOCKS:
                    if tag == self.block_tag:
                        self._close()
                elif tag in self.INLINE and self.INLINE[tag] in self.inline:
                    self.inline.remove(self.INLINE[tag])

            def handle_data(self, data):
                if not data:
                    return
                if self.current is None:
                    if not data.strip():
                        return
                    self._open('p')            # texto suelto fuera de bloque
                if self.block_tag != 'pre':
                    data = data.replace('\n', ' ')
                if not self.inline:
                    self.current.addText(data)
                    return
                props = {}
                if 'bold' in self.inline:
                    props['fontweight'] = 'bold'
                if 'italic' in self.inline:
                    props['fontstyle'] = 'italic'
                if 'underline' in self.inline:
                    props.update(textunderlinestyle='solid', textunderlinewidth='auto',
                                 textunderlinecolor='font-color')
                if 'strike' in self.inline:
                    props['textlinethroughstyle'] = 'solid'
                self._inline_counter += 1
                name = f"Inline_{self._inline_counter}"
                span_style = Style(name=name, family="text")
                span_style.addElement(TextProperties(**props))
                self.odt.automaticstyles.addElement(span_style)
                span = Span(stylename=name)
                span.addText(data)
                self.current.addElement(span)

            def close(self):
                super().close()
                self._close()

        parser = QuillParser(doc_odt)
        parser.feed(self.content)
        parser.close()

        buf = BytesIO()
        doc_odt.save(buf)
        return buf.getvalue()
