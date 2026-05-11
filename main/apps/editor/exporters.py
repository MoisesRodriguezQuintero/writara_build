import re
from django.template.loader import render_to_string


class DocumentExporter:
    def __init__(self, doc):
        self.doc = doc

    def to_html(self):
        return render_to_string('editor/export.html', {'doc': self.doc})

    def to_markdown(self):
        try:
            import html2text
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.body_width = 0
            return f"# {self.doc.title}\n\n" + h.handle(self.doc.content)
        except ImportError:
            clean = re.sub(r'<[^>]+>', '', self.doc.content)
            return f"# {self.doc.title}\n\n{clean}"

    def to_odt(self) -> bytes:                         # ← indentado dentro de la clase
        from odf.opendocument import OpenDocumentText
        from odf.style import Style, TextProperties, ParagraphProperties
        from odf.text import H, P, Span
        from io import BytesIO
        from html.parser import HTMLParser

        doc_odt = OpenDocumentText()

        h1_style = Style(name="Heading1", family="paragraph")
        h1_style.addElement(TextProperties(fontsize="18pt", fontweight="bold"))
        doc_odt.styles.addElement(h1_style)

        h2_style = Style(name="Heading2", family="paragraph")
        h2_style.addElement(TextProperties(fontsize="14pt", fontweight="bold"))
        doc_odt.styles.addElement(h2_style)

        h3_style = Style(name="Heading3", family="paragraph")
        h3_style.addElement(TextProperties(fontsize="12pt", fontweight="bold"))
        doc_odt.styles.addElement(h3_style)

        body_style = Style(name="Body", family="paragraph")
        body_style.addElement(TextProperties(fontsize="11pt"))
        body_style.addElement(ParagraphProperties(lineheight="180%"))
        doc_odt.styles.addElement(body_style)

        title_p = H(outlinelevel=1, stylename="Heading1")
        title_p.addText(self.doc.title)
        doc_odt.text.addElement(title_p)

        class QuillParser(HTMLParser):
            def __init__(self, odt_doc):
                super().__init__()
                self.odt = odt_doc
                self.current_p = None
                self.tag_stack = []
                self.bold = False
                self.italic = False
                self._inline_counter = 0

            def handle_starttag(self, tag, attrs):
                self.tag_stack.append(tag)
                if tag in ('h1', 'h2', 'h3'):
                    level = int(tag[1])
                    self.current_p = H(outlinelevel=level, stylename=f"Heading{level}")
                elif tag == 'p':
                    self.current_p = P(stylename="Body")
                elif tag in ('strong', 'b'):
                    self.bold = True
                elif tag in ('em', 'i'):
                    self.italic = True

            def handle_endtag(self, tag):
                if self.tag_stack and self.tag_stack[-1] == tag:
                    self.tag_stack.pop()
                if tag in ('h1', 'h2', 'h3', 'p') and self.current_p is not None:
                    self.odt.text.addElement(self.current_p)
                    self.current_p = None
                elif tag in ('strong', 'b'):
                    self.bold = False
                elif tag in ('em', 'i'):
                    self.italic = False

            def handle_data(self, data):
                text = data.strip()
                if not text or self.current_p is None:
                    return
                if self.bold or self.italic:
                    self._inline_counter += 1
                    style_name = f"Inline_{self._inline_counter}"
                    props = {}
                    if self.bold:
                        props['fontweight'] = 'bold'
                    if self.italic:
                        props['fontstyle'] = 'italic'
                    span_style = Style(name=style_name, family="text")
                    span_style.addElement(TextProperties(**props))
                    self.odt.automaticstyles.addElement(span_style)
                    span = Span(stylename=style_name)
                    span.addText(text)
                    self.current_p.addElement(span)
                else:
                    self.current_p.addText(text)

        parser = QuillParser(doc_odt)
        parser.feed(self.doc.content)

        buf = BytesIO()
        doc_odt.save(buf)
        return buf.getvalue()