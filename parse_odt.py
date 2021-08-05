import xml.etree.ElementTree as ET
import zipfile
from io import BytesIO

ns = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "style": "urn:oasis:names:tc:opendocument:xmlns:style:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "fo": "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0",
    "loext": "urn:org:documentfoundation:names:experimental:office:xmlns:loext:1.0",
}

def to_ns(value):
    ns_key, value = value.split(':')
    return "{%s}%s" % (ns[ns_key], value)

known_styles = {
    to_ns("style:header-style"): [],
    to_ns("style:footer-style"): [],
    to_ns("style:graphic-properties"): [],
    to_ns("loext:graphic-properties"): [],
    to_ns("text:outline-level-style"): [],
    to_ns("style:page-layout-properties"): ["fo:page-width", "fo:page-height", "fo:print-orientation", "fo:margin-top", "fo:margin-bottom", "fo:margin-right", "fo:margin-left", "fo:line-height"],
    to_ns("style:paragraph-properties"): ["fo:text-align", "fo:break-before", "fo:margin-left", "fo:margin-right", "fo:margin-top", "fo:margin-bottom", "fo:text-indent"],
    to_ns("style:text-properties"): ["style:font-name", "fo:font-style", "fo:font-weight", "fo:font-size", "style:text-underline-style"],
}

def to_inches(value):
    assert value[-2:] == "in"
    return float(value[:-2])

def parse_style(style):
    result = {}
    if style.tag == to_ns("style:page-layout"):
        result["page-usage"] = style.attrib.get(to_ns("style:page-usage"))
    psn = style.attrib.get(to_ns("style:parent-style-name"))
    if psn:
        result['parent-style-name'] = psn
    for c in style:
        keys = known_styles.get(c.tag)
        assert not keys is None, "Unknown style tag %s" % c.tag
        for s in keys:
            key = to_ns(s)
            s = s.split(':')[-1] # drop namespace
            if key in c.attrib:
                result[s] = c.attrib.get(key)
    return result

def merge_styles(*styles):
    res = {}
    for s in styles:
        res |= s
    return res

class Paragraph:
    def __init__(self):
        self.alignment = 'start'
        self.margin_top = 0
        self.margin_bottom = 0
        self.margin_left = 0
        self.margin_right = 0
        self.text_indent = 0
        self.line_height_factor = 1
        self.is_break = False
        self.element = None
        self.style = None

    @staticmethod
    def from_odt_element(element, style, index):
        result = Paragraph()
        result.alignment = style.get('text-align', 'start')
        result.margin_top = to_inches(style.get('margin-top', 0))
        result.margin_bottom = to_inches(style.get('margin-bottom', 0))
        result.margin_left = to_inches(style.get('margin-left', 0))
        result.margin_right = to_inches(style.get('margin-right', 0))
        result.text_indent = to_inches(style.get('text-indent', 0))
        line_height = style.get('line-height', "100%")
        assert line_height[-1] == "%"
        result.line_height_factor = int(line_height[:-1]) / 100
        result.is_break = style.get('break-before') == "page"
        if index == 0:
            result.is_break = False
        result.element = element
        result.style = style
        return result

class ODT:
    def __init__(self, filename):
        self.styles = {}

        z = zipfile.ZipFile(filename)
        content = z.read('content.xml')

        root = ET.fromstring(content)
        styles = root.find('office:automatic-styles', ns)
        for s in styles:
            self.styles[s.attrib[to_ns("style:name")]] = parse_style(s)
        self.body = root.find('office:body', ns)
        self.text = self.body.find('office:text', ns)

        # styles.xml
        styles = z.read('styles.xml')
        root = ET.fromstring(styles)
        styles = root.find('office:styles', ns)
        for s in styles:
            style_name = s.attrib.get(to_ns("style:name"))
            if style_name is None: continue
            self.styles[style_name] = parse_style(s)

        # parse page style
        styles = root.find('office:automatic-styles', ns)
        for s in styles:
            self.styles[s.attrib[to_ns("style:name")]] = parse_style(s)
        master = root.find('office:master-styles', ns)
        master_page = master.find('style:master-page', ns)
        master_page_style = master_page.attrib.get(to_ns('style:page-layout-name'))
        mps = self.styles[master_page_style]
        for key, value in mps.items():
            try:
                value = float(value.replace('in',''))
            except:
                pass
            setattr(self, key.replace('-', '_'), value)

        # 2nd pass: merge all parent styles recursively
        def merge_parent_style(style):
            if style.get('parent-style-name'):
                parent = self.styles[style['parent-style-name']]
                merge_parent_style(parent)
                for key, value in parent.items():
                    if not key in style:
                        style[key] = value
                del style['parent-style-name']
        for style in self.styles.values():
            merge_parent_style(style)

    def parse_paragraphs(self):
        paragraphs = self.text.iter()
        result = []
        for i, p in enumerate(paragraphs):
            if p.tag in [to_ns("text:h"), to_ns("text:p")]:
                style_name = p.attrib.get(to_ns('text:style-name'))
                style = self.styles[style_name]
                result.append(Paragraph.from_odt_element(p, style, i))
        return result

    # returns text and style information recursivly from the given xml element
    # returns a list of (style, text) pairs
    def parse(self, element, style):
        result = []
        if element.text:
            result.append([style, element.text])
        for child in element:
            el_style_name = child.attrib.get(to_ns('text:style-name'))
            if el_style_name:
                el_style = self.styles[el_style_name]
                sub_style = merge_styles(style, el_style)
            else:
                sub_style = merge_styles(style)

            tag = child.tag;
            if tag == to_ns("text:line-break"):
                result.append([sub_style, "\r\n"])
            elif tag == to_ns("text:tab"):
                result.append([sub_style, "\t"])
            elif tag == to_ns("text:s"):
                c = child.attrib.get(to_ns('text:c'))
                if c:
                    spaceCount = int(c)
                else:
                    spaceCount = 1
                result.append([sub_style, " " * spaceCount])
            if tag == to_ns("text:soft-page-break"):
                result.append([sub_style, "\f"])
            else:
                result.extend(self.parse(child, sub_style))
            if child.tail:
                result.append([style, child.tail])
        return result
