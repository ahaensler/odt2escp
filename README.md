# Print Open Office documents with Epson ESC/P2 printers
## Introduction
A printer driver for ESC/P2 printers and ODT documents. The printer will use native text mode and achive better quality and speed compared to raster mode. A free font is included that provides correct spacing of characters in modern WYSIWYG editors.

## Dependencies
Python 3.9 or later

## Getting Started
Clone the repository
```
git clone https://github.com/ahaensler/odt2escp
cd odt2escp
```
Install the font `EpsonRomanProportional.ttf` and prepare an ODT document using the font.

Print the document with
```
python odt2escp.py -o /dev/usb/lp0 document.odt
```

## Usage
```
usage: odt2escp.py [-h] [--output OUTPUT_FILENAME] [--testpage] [--character-table CHARACTER_TABLE] [path]

Print ODT documents with dot matrix printers that support the ESC/P2 format

positional arguments:
  path                  path to an ODT file

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT_FILENAME, -o OUTPUT_FILENAME
                        output device
  --testpage, -t        print a test page with font samples
  --character-table CHARACTER_TABLE, -c CHARACTER_TABLE
                        select a character table, for example PC437, PC1250
```

## Limitations
Only basic styling is supported
- Bold, italic and underline font styles
- Left, center, right and justified text alignment
- Basic page and paragraph spacing

More advanced elements are not supported, including graphics, user-defined tabs, tables, landscape orientation, lists, etc.

Fonts are limited to the proprietary fonts that come with printers. There are usually a couple of proportional fonts available (Roman, Sans Serif, Script). Supported font sizes are 8, 10.5, 12, 14, 16, 18, 20, 21, 22, 24, 26, 28, 30 and 32 points.

Unicode is not fully supported. All characters have to map to the legacy codepages that come with the printer.

## Setting Linux Printer Permissions
You may want to modify permissions of the printer's device file and allow users to send raw data to the printer. Create a new udev configuration file, for example `99-usb-printer.rules`. Paths can vary by distribution.

In case of a USB printer
```
KERNEL=="lp0", SUBSYSTEMS=="usbmisc", MODE="0666"
```

Reload udev rules.
```
udevadm control --reload-rules
udevadm trigger
```

The device file should allow user access now.
```
ls -l /dev/usb/lp0
```
