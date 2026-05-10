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
