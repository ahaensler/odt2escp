from epson_firmware import *
from parse_odt import ODT, Paragraph
import os
import argparse

# Represents a word and its spacing information
class Word:
    def __init__(self, text, height = None, may_break = None):
        self.text = text
        self.size = 0
        self.height = 0 if height is None else height
        self.may_break = may_break # a break is allowed after the word

    def is_space(self):
        return self.text == b" "

    def is_tab(self):
        return self.text == b"\t"

    def is_soft_hyphen(self):
        return self.text and self.text[-1] == 0xad

    def append(self, other):
        self.text += other.text
        self.size += other.size
        self.may_break = other.may_break
        self.height = max(self.height, other.height)

    def __repr__(self):
        return str(self.text)

class PrinterOutput:
    def __init__(self, file, page_width=8.5, page_height=11, page_usage=None, margin_top=.5, margin_bottom=.5, margin_right=.5, margin_left=.5, character_table="PC1250"):
        self.outfile = file
        self.line = [] # the current line
        self.word = Word(bytearray()) # the current word
        self.line_size = 0
        self.line_height = 0
        self.page_width = page_width
        self.page_height = page_height
        self.page_usage = page_usage
        self.margin_top = margin_top
        self.margin_bottom = margin_bottom
        self.margin_right = margin_right
        self.margin_left = margin_left
        self.last_margin_left = None
        self.max_text_width = page_width - margin_left - margin_right
        self.allow_leading_whitespace = False
        self.allow_line_indent = False
        self.default_tab_spacing = 12.5/25.4
        self.font_size = 10.5
        self.character_table = None

        self.esc('@')
        self.set_line_spacing(30)
        self.load_character_table(character_table)
        self.esc('t', 1) # select table 1
        self.set_font(font_name_to_code("Roman"))
        self.esc('p', 1) # proportional mode
        self.pitch = None # None means proportional pitch
        self.esc('x', 1) # letter quality
        self.set_page_margins(1)

    def set_page_margins(self, page_number):
        margin_left = self.margin_left
        if self.page_usage and self.page_usage == "mirrored" and page_number % 2:
            margin_left = self.margin_right
        if margin_left == self.last_margin_left:
            return
        top = int((self.margin_top-0.1)*360)
        bottom = int((self.page_height - self.margin_bottom + 0.2) * 360)
        self.esc('(c', 4,0, top & 0xff, (top >> 8) & 0xff, bottom & 0xff, (bottom >> 8) & 0xff) # set page length
        self.esc('l', int(margin_left * 10 - 1)) # set left margin
        self.last_margin_left = margin_left

    def load_character_table(self, table_name, no_write = None):
        if not no_write and self.character_table == table_name: return
        code = character_table_to_code.get(table_name)
        assert code, "Unsupported character table " + str(table_name)
        table_index = 1
        result = self.esc('(t',3,0, table_index, *code, no_write = no_write) # PC1251 -> table 1
        if no_write:
            return result
        else:
            self.character_table = table_name

    def get_max_paragraph_width(self):
        res = self.max_text_width - self.paragraph.margin_left - self.paragraph.margin_right
        if self.allow_line_indent:
            res -= self.paragraph.text_indent
        return res

    def next_tab(self, position):
        tab = int(position / self.default_tab_spacing) + 1
        tab *= self.default_tab_spacing
        if tab >= self.max_text_width:
            return float("inf")
        else:
            return tab

    def set_font(self, code, no_write = None):
        self.font_code = code
        return self.esc('k', code, no_write=no_write) # typeface roman

    def set_line_spacing(self, spacing):
        assert spacing >= 0 and spacing <= 255
        if spacing == 30:
            self.esc('2') # line spacing 1/6 inch
        else:
            self.esc('3', spacing) # line spacing n/180 inch
        self.line_spacing = spacing

    def write(self, data):
        n = os.write(self.outfile, data)
        assert n == len(data)

    def esc(self, *args, no_write = None):
        cmd = bytearray()
        cmd += b"\x1b"
        for arg in args:
            if type(arg) == str:
                cmd += arg.encode('latin-1')
            elif type(arg) == int:
                cmd += arg.to_bytes(1, 'little')
        if no_write is None:
            self.write(cmd)
        else:
            return cmd

    def set_horizontal_position(self, pos, no_write=None):
        pos = int(pos*60)
        cmd = bytearray()
        cmd.append(0x1b)
        cmd += b'$'
        cmd.append(pos & 0xff)
        cmd.append((pos>>8) & 0xff)
        if no_write is None:
            self.write(cmd)
        else:
            return cmd

    def set_relative_vertical_position(self, pos, no_write=None):
        pos = int(pos*360)
        cmd = bytearray()
        cmd.append(0x1b)
        cmd += b'(v\x02\x00'
        cmd.append(pos & 0xff)
        cmd.append((pos>>8) & 0xff)
        if no_write is None:
            self.write(cmd)
        else:
            return cmd

    # second pass of assembling words into a line, this time for final layout
    def join_words(self, words, last_line):
        # remove whitespace at end
        for trailing_space, w in enumerate(reversed(words)):
            if not w.is_space():
                break
            self.line_size -= w.size
        else:
            trailing_space = 0
        words = words[:len(words)-trailing_space]

        # joins words to a line and positions them according to tabs and spaces
        result = b""
        start_x = 0
        if self.paragraph.alignment == "start":
            offset = 0
        elif self.paragraph.alignment == "center":
            offset = (self.get_max_paragraph_width() - self.line_size)/2
        elif self.paragraph.alignment == "end":
            offset = self.get_max_paragraph_width() - self.line_size
        elif self.paragraph.alignment == "justify":
            offset = 0
            if last_line:
                space_grow_factor = 1
                last_tab = float("inf")
            else:
                # justification starts after tabs
                try:
                    last_tab = next(i for i, v in enumerate(reversed(words)) if v.is_tab())
                except StopIteration:
                    last_tab = len(words)
                last_tab = len(words) - 1 - last_tab
                # replace spaces
                spaces = [w for w in words[last_tab + 1:] if w.is_space()]
                spaces_width = sum(w.size for w in spaces)
                if spaces_width:
                    width_to_add = self.get_max_paragraph_width() - self.line_size
                    space_grow_factor = width_to_add / spaces_width + 1
                else:
                    space_grow_factor = 1
        offset += self.paragraph.margin_left
        if self.allow_line_indent:
            offset += self.paragraph.text_indent
        if offset:
            result += self.set_horizontal_position(offset, no_write=True)

        for i, w in enumerate(words):
            if w.is_tab():
                start_x = self.next_tab(start_x)
                result += self.set_horizontal_position(offset + start_x, no_write=True)
            elif self.paragraph.alignment == "justify" and w.is_space() and i > last_tab:
                start_x += w.size * space_grow_factor
                result += self.set_horizontal_position(offset + start_x, no_write=True)
            else:
                result += w.text
                start_x += w.size
        return result

    def process_line(self, last_line = None):
        self.line = self.join_words(self.line, last_line)
        if self.line_height == 0:
            self.line_height = 10.5
        new_line_spacing = int(self.line_height/72*180*1.15*self.paragraph.line_height_factor)
        if new_line_spacing != self.line_spacing:
            self.set_line_spacing(new_line_spacing)
        self.write(b"\r\n")
        self.write(self.line)
        self.line = []
        self.line_size = 0
        self.line_height = 0
        self.allow_leading_whitespace = False
        self.allow_line_indent = False

    def new_paragraph(self, paragraph):
        self.paragraph = paragraph
        if self.paragraph.margin_top:
            self.set_relative_vertical_position(self.paragraph.margin_top)
        self.allow_leading_whitespace = True
        self.allow_line_indent = True

    def paragraph_break(self):
        self.add_word()
        self.process_line()
        self.allow_leading_whitespace = True

    def end_paragraph(self):
        self.add_word()
        self.process_line(last_line = True)
        if self.paragraph.margin_bottom:
            self.set_relative_vertical_position(self.paragraph.margin_bottom)

    def new_page(self, page_number):
        self.add_word()
        if self.line:
            self.process_line()
        self.write(b"\r")
        self.write(b"\f") # form feed
        if self.page_usage == "mirrored":
            self.set_page_margins(page_number)

    def end(self):
        self.new_page(0)
        self.esc('@')

    def add_word(self):
        if self.word.size:
            if self.line and self.line[-1].is_soft_hyphen():
                # remove unused soft hyphen
                self.line[-1].text = self.line[-1].text[:-1]
                soft_hyphen_size = 30/360 * self.font_scale_factor
                self.line[-1].size -= soft_hyphen_size
                self.line_size -= soft_hyphen_size
            self.line.append(self.word)
            self.line_height = max(self.line_height, self.word.height)
            self.line_size += self.word.size
            self.word = Word(bytearray())

    def get_character_width(self, c):
        if c == 9:
            return 30
        return proportional_character_width.get(c)

    # split text into words and encode them according to the selected character table
    def text_to_words(self, text, height, encoding):
        words = []
        i = 0
        while i < len(text):
            c = ord(text[i])
            if c == 9 or c == 32:
                if i > 0:
                    words.append(Word(text[0:i], height=height, may_break = True))
                words.append(Word(text[i:i+1], height=height, may_break = True))
                text = text[i+1:]
                i = 0
            # hyphen, soft hyphen and dash
            elif c in [ord('-'), 0xad, ord('–'), ord('—')]:
                words.append(Word(text[0:i+1], height=height, may_break = True))
                text = text[i+1:]
                i = 0
            else:
                i += 1
        if len(text):
            words.append(Word(text, height=height))

        # calculate size
        for word in words:
            word.size = 0
            for c in word.text:
                size = self.get_character_width(c)
                assert not size is None, "Undefined character code %s (%x, %s)" % (c, ord(c), word.text[:10])
                word.size += size
            word.size = word.size / 360 * self.font_scale_factor
            word.text = word.text.encode(encoding)
        return words

    def get_tab_size(self):
        abs_pos = self.paragraph.margin_right + self.line_size
        res = self.next_tab(abs_pos) - abs_pos
        return res

    # first pass of assembling words into a line, decides on where to break lines
    def add_text(self, text, font_name, font_size, weight, style, underline, position):
        character_table = self.character_table
        encoding = character_tables[character_table][0]
        try_character_tables = ['PC1250', 'PC437', 'PC869']
        while 1:
            try:
                text.encode(encoding)
                break
            except UnicodeEncodeError as error:
                if error.start:
                    self.break_text(text[:error.start], font_name, font_size, weight, style, underline, position, character_table)
                text = text[error.start:]
                char = text[0]
                for character_table in try_character_tables:
                    try:
                        encoding = character_tables[character_table][0]
                        char.encode(encoding)
                        break
                    except:
                        continue
                else:
                    raise Exception("The character %s cannot be encoded" % char)
                continue

        if len(text):
            self.break_text(text, font_name, font_size, weight, style, underline, position, character_table)

    def break_text(self, text, font_name, font_size, weight, style, underline, position, character_table):
        encoding = character_tables[character_table][0]
        self.font_scale_factor = font_size / 10.5
        self.whitespace_width = proportional_character_width.get(' ') / 360 * self.font_scale_factor

        # preserve leading whitespace of the first line in a paragraph
        if self.allow_leading_whitespace and len(self.line) == 0:
            try:
                pre_whitespace = next(i for i, v in enumerate(text) if v != 32)
            except StopIteration:
                pre_whitespace = len(text)
            if pre_whitespace:
                w = Word(text[:pre_whitespace])
                w.size = self.whitespace_width * pre_whitespace
                self.line.append(w)
                text = text[pre_whitespace:]
                self.line_size += w.size
        words = self.text_to_words(text, font_size, encoding)

        # apply font settings
        self.word.height = max(self.word.height, font_size)
        font_code = font_name_to_code(font_name)
        if font_code in proportional_fonts: pitch = None
        else: pitch = 10

        if not font_code in character_tables[character_table][1]:
            print("Falling back to PC437")
            self.word.text += self.load_character_table('PC437', no_write = True)
        elif self.character_table != character_table:
            self.word.text += self.load_character_table(character_table, no_write = True)
        if font_size != self.font_size or pitch != self.pitch:
            if font_code in proportional_fonts:
                self.word.text += b"\x1bX\x01"
                self.word.text.append(int(font_size*2))
                self.word.text.append(0)
            else:
                self.word.text += b"\x1bp\x00" # turn off proportional mode
                self.word.text += b"\x1bP" # cancel multipoint, select 10 cpi
        if style == "italic":
            self.word.text += b"\x1b4"
        if weight == "bold":
            self.word.text += b"\x1bE"
        if underline == "solid":
            self.word.text += b"\x1b-\x01"
        previous_font = None
        if font_code != self.font_code:
            previous_font = self.font_code
            self.word.text += self.set_font(font_code, no_write=True)
        if position:
            if position.startswith("super"):
                self.word.text += b"\x1bS\x00"
            elif position.startswith("sub"):
                self.word.text += b"\x1bS\x01"

        # determine line breaks
        for i, w in enumerate(words):
            if w.is_space() or w.is_tab():
                self.add_word()
            if w.is_space():
                # always add spaces - they will be ignored later
                self.word.text += w.text
                self.word.size += w.size
                self.add_word()
                continue
            if w.is_tab(): w.size = self.get_tab_size()
            new_end = self.line_size + self.word.size + w.size
            # the condition which determines when to break a line
            # there's some added allowance for rounding errors in the font used
            if self.line_size and new_end > self.get_max_paragraph_width() + 5/360:
                # some rules for line breaks
                # don't break between tab and word
                if self.line[-1].is_tab() and not (self.word.is_tab() or self.word.is_space()):
                    tab = self.line[-1]
                    self.line_size -= tab.size
                    self.line = self.line[:-1]
                    self.process_line()
                    tab.size = self.get_tab_size()
                    self.line.append(tab)
                    self.line_size += tab.size
                    self.line_height = tab.height
                else:
                    # don't break ongoing word without space
                    if self.word.may_break:
                        self.add_word()
                    self.process_line()
                if w.is_tab(): w.size = self.get_tab_size()
            if self.word.may_break:
                self.add_word()
            self.word.append(w)

        if self.word.is_tab(): 
            self.add_word()

        # reset font to default
        if self.character_table != character_table:
            self.word.text += self.load_character_table(self.character_table, no_write = True)
        if font_size != 10.5:
            self.word.text += b"\x1bX\x00\x15\x00"
        if style == "italic":
            self.word.text += b"\x1b5"
        if weight == "bold":
            self.word.text += b"\x1bF"
        if underline == "solid":
            self.word.text += b"\x1b-\x00"
        if previous_font:
            self.word.text += self.set_font(previous_font, no_write=True)
        if position:
            self.word.text += b"\x1bT"

def print_font_test_page(f):
    printer = PrinterOutput(f)
    fonts = [
        'Roman',
        'SansSerif',
        'Courier',
        'Prestige',
        'Script',
        'OCR-B',
        'Orator',
        'Orator-S',
        'Script C',
        'Roman T',
        'Sans serif H',
    ]
    for font_name in fonts:
        code = font_name_to_code(font_name)
        sizes = [10.5, 14] if code in scalable_fonts else [10.5]
        for size in sizes:
            printer.new_paragraph(Paragraph())
            printer.add_text("c=%d %.1fpt - The quick brown fox jumps over the lazy dog" % (code, size), font_name, size, None, None, None, None)
            printer.end_paragraph()
    printer.end()

def get_style_params(style):
    font_name = style.get('font-name', 'EpsonRomanProportional')
    font_size = style.get('font-size', '12pt')
    if font_size:
        assert font_size[-2:] == "pt"
        font_size = float(font_size[:-2])
    font_weight = style.get('font-weight')
    font_style = style.get('font-style')
    underline = style.get('text-underline-style')
    position = style.get('text-position')
    #assert font_name in supported_fonts, 'Unknown font ' + str(font_name)
    assert font_size in supported_sizes, 'Font size has to be one of ' + str(supported_sizes)
    return font_name, font_size, font_weight, font_style, underline, position

def print_odt(args, f):
    doc = ODT(args.path)
    printer = PrinterOutput(f, doc.page_width, doc.page_height, doc.page_usage, doc.margin_top, doc.margin_bottom, doc.margin_left, doc.margin_right, args.character_table)

    page_number = 1
    for paragraph in doc.parse_paragraphs():
        if paragraph.is_break:
            page_number += 1
            if page_number-1 in args.pages:
                printer.new_page(page_number)

        result = doc.parse(paragraph.element, paragraph.style)

        if page_number in args.pages or \
            (result and result[0][1] == "\f" and page_number + 1 in args.pages):
            result = doc.parse(paragraph.element, paragraph.style)
            printer.new_paragraph(paragraph)
        else:
            printer.paragraph = paragraph
            printer.allow_leading_whitespace = False
            printer.allow_line_indent = False

        for style, text in result:
            font_style = get_style_params(style)
            if text == "\r\n":
                if page_number in args.pages:
                    printer.paragraph_break()
            elif text == "\f":
                page_number += 1
                if page_number-1 in args.pages:
                    printer.new_page(page_number)
            else:
                if page_number in args.pages:
                    printer.set_page_margins(page_number)
                    printer.add_text(text, *font_style)

        if page_number in args.pages:
            printer.end_paragraph()
    printer.end()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Print ODT documents with dot matrix printers that support the ESC/P2 format')
    parser.add_argument('--output', '-o', dest='output_filename', default=None, help='output device')
    parser.add_argument('--testpage', '-t', dest='testpage', action='store_true', help='print a test page with font samples')
    parser.add_argument('--character-table', '-c', dest='character_table', default="PC1250", help='select a character table, for example PC437, PC1250')
    parser.add_argument('--page', '-p', dest='pages', help='start from given page number')
    parser.add_argument('--odd', '-d', dest='odd', action='store_true', help='print only odd pages')
    parser.add_argument('--even', '-e', dest='even', action='store_true', help='print only even pages')
    parser.add_argument('path', nargs='?', help='path to an ODT file')
    args = parser.parse_args()

    if args.pages:
        args.pages = range(int(args.pages), 10000)
    if not args.pages:
        args.pages = range(1,10000)
    if args.odd:
        assert not args.even
        args.pages = [p for p in args.pages if p % 2]
    elif args.even:
        args.pages = [p for p in args.pages if p % 2 == 0]


    # validation
    if not args.testpage and (not args.path or not os.path.exists(args.path)):
        parser.print_help()
        exit()

    if args.output_filename:
        f = os.open(args.output_filename, os.O_WRONLY)
    else:
        f = 1 # stdout handle

    if args.testpage:
        print_font_test_page(f)
    else:
        print_odt(args, f)

    os.close(f)
