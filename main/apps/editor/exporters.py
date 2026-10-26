from io import BytesIO
from html.parser import HTMLParser

from django.template.loader import render_to_string

from main.utils import clean_html, html_to_text


def _blocked_url_fetcher(url, *args, **kwargs):
    """WeasyPrint solo puede cargar recursos incrustados (data:). Bloquea http(s)
    y file:// para que un documento no pueda leer ficheros locales ni hacer
    peticiones de red desde el servidor al generar el PDF."""
    from weasyprint import default_url_fetcher
    if url.startswith('data:'):
        return default_url_fetcher(url, *args, **kwargs)
    raise ValueError(f'Recurso externo bloqueado: {url}')


class DocumentExporter:
    def __init__(self, doc):
        self.doc = doc
        # Todo el HTML de usuario se sanea antes de exportarlo
        self.content = clean_html(doc.content)

    def to_html(self):
        return render_to_string('editor/export.html', {'doc': self.doc})

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
        from odf.style import Style, TextProperties, ParagraphProperties
        from odf.text import H, P, Span, LineBreak

        doc_odt = OpenDocumentText()

        for level, size in ((1, '18pt'), (2, '14pt'), (3, '12pt')):
            style = Style(name=f"Heading{level}", family="paragraph")
            style.addElement(TextProperties(fontsize=size, fontweight="bold"))
            doc_odt.styles.addElement(style)

        body_style = Style(name="Body", family="paragraph")
        body_style.addElement(TextProperties(fontsize="11pt"))
        body_style.addElement(ParagraphProperties(lineheight="180%"))
        doc_odt.styles.addElement(body_style)

        quote_style = Style(name="Quote", family="paragraph")
        quote_style.addElement(TextProperties(fontsize="11pt", fontstyle="italic"))
        quote_style.addElement(ParagraphProperties(marginleft="1cm", lineheight="180%"))
        doc_odt.styles.addElement(quote_style)

        code_style = Style(name="Code", family="paragraph")
        code_style.addElement(TextProperties(fontsize="10pt", fontfamily="Courier New"))
        doc_odt.styles.addElement(code_style)

        list_style = Style(name="ListItem", family="paragraph")
        list_style.addElement(TextProperties(fontsize="11pt"))
        list_style.addElement(ParagraphProperties(marginleft="0.8cm", lineheight="160%"))
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
