"""HTML helpers for the reports tests: find elements by what the user sees or follows (links, ids, controls)."""
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlsplit

VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}


class _Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements, self._open = [], []

    def handle_starttag(self, tag, attrs):
        element = dict(attrs, tag=tag, text='', inner=[])
        if 'href' in element:
            url = urlsplit(element['href'] or '')
            element.update(path=url.path, query=dict(parse_qsl(url.query)))
        for parent in self._open:
            parent['inner'].append(element)
        self.elements.append(element)
        if tag not in VOID_TAGS:
            self._open.append(element)

    def handle_endtag(self, tag):
        for i in range(len(self._open) - 1, -1, -1):
            if self._open[i]['tag'] == tag:
                del self._open[i:]
                return

    def handle_data(self, data):
        for element in self._open:
            element['text'] += data


def page(response):
    """Every element of the page as a dict: its attributes (unescaped) plus 'tag', 'text' (all text inside)
    and 'inner' (all elements inside). Elements with an href also get 'path' and 'query' ({param: value})."""
    parser = _Elements()
    parser.feed(response.content.decode())
    return parser.elements


def links_to(elements, path, **params):
    """Elements linking to `path` whose query has at least these params."""
    return [e for e in elements if e.get('path') == path and params.items() <= e['query'].items()]


def with_id(elements, element_id):
    return [e for e in elements if e.get('id') == element_id]


def payment_checkboxes(elements):
    """{(expense id, checked, URL it saves to)} of the payment checkboxes, however many times each is rendered."""
    return {(int(e['data-expense-id']), 'checked' in e, e['data-url'])
            for e in elements if e['tag'] == 'input' and e.get('data-expense-id')}
