supported_sizes = [8, 10, 10.5, 12, 14, 16, 18, 20, 21, 22, 24, 26, 28, 30, 32] # 20=21 and 10=10.5
supported_fonts = ['EpsonRomanProportional', 'EpsonSansSerifProportional']
scalable_fonts = [0, 1, 10, 11]

# all fonts work in proportional mode, but not all look right
proportional_fonts = [0, 1, 9, 10, 11]

# mapping from character table name to
# - python encoding name
# - supported font codes
# some character tables only support certain fonts
character_tables = {
    'PC437': ('cp437', range(12)),
    'PC1250': ('windows-1250', [0,1,2,3,4]),
    'PC1251': ('windows-1251', [0,1,2,3,4]),
}

_font_name_to_code = {
    'EpsonRomanProportional': 0,
    'EpsonSansSerifProportional': 1,
    'Roman': 0,
    'SansSerif': 1,

    'Courier': 2,
    'Prestige': 3,
    'Script': 4,
    'OCR-B': 5,
    # 'OCR-A': 6,
    'Orator': 7,
    'Orator-S': 8, # includes small caps
    'Script C': 9,

    'Roman T': 10, # thick
    'Sans serif H': 11, # heavy
    # 'SV Busaba': 30,
    # 'SV Jittra': 31,
}

def font_name_to_code(font_name):
    result = _font_name_to_code.get(font_name)
    if result is None:
        #print("Unknown font", font_name)
        return 0
    return result

character_table_to_code = {
    'PC437': (1, 0),
    'PC850': (1, 0),
    'ECMA-94-1': (17, 0),
    'ISO 8859-1': (29, 16),
    'PC1250': (48, 0),
    'PC1251': (49, 0),
}

# should represent PC1250 codes
# TODO: translate to unicode
proportional_character_width = {
    10: 0,
    13: 0,
    32: 30,
    33: 18,
    34: 30,
    35: 30,
    36: 30,
    37: 36,
    38: 36,
    39: 18,
    40: 24,
    41: 24,
    42: 30,
    43: 30,
    44: 18,
    45: 30,
    46: 18,
    47: 30,
    48: 30,
    49: 30,
    50: 30,
    51: 30,
    52: 30,
    53: 30,
    54: 30,
    55: 30,
    56: 30,
    57: 30,
    58: 18,
    59: 18,
    60: 30,
    61: 30,
    62: 30,
    63: 30,
    64: 36,
    65: 36,
    66: 36,
    67: 36,
    68: 36,
    69: 36,
    70: 36,
    71: 36,
    72: 36,
    73: 24,
    74: 30,
    75: 36,
    76: 36,
    77: 42,
    78: 36,
    79: 36,
    80: 36,
    81: 36,
    82: 36,
    83: 36,
    84: 36,
    85: 42,
    86: 36,
    87: 42,
    88: 36,
    89: 36,
    90: 30,
    91: 24,
    92: 30,
    93: 24,
    94: 30,
    95: 30,
    96: 18,
    97: 30,
    98: 36,
    99: 30,
    100: 36,
    101: 30,
    102: 24,
    103: 36,
    104: 36,
    105: 18,
    106: 24,
    107: 36,
    108: 18,
    109: 42,
    110: 36,
    111: 30,
    112: 36,
    113: 36,
    114: 30,
    115: 30,
    116: 24,
    117: 36,
    118: 36,
    119: 42,
    120: 30,
    121: 36,
    122: 30,
    123: 24,
    124: 18,
    125: 24,
    126: 30,
    128: 36,
    129: 36,
    130: 18, # single lower quotation mark
    131: 30,
    132: 30, # lower quotation marks
    133: 36, # ellipsis
    134: 30,
    135: 30,
    136: 30, # Euro
    137: 36, # per thousand
    138: 30,
    139: 18,
    140: 18,
    141: 18,
    142: 36,
    143: 36,
    144: 36,
    145: 18, # single left quotation mark
    146: 18, # single right quotation mark
    147: 30,
    148: 30,
    149: 30,
    150: 36, # en dash
    151: 42, # long dash
    152: 36,
    153: 36, # trademark
    154: 42,
    155: 30,
    156: 30,
    157: 36,
    158: 42,
    159: 30,
    160: 30,
    161: 18,
    162: 30,
    163: 36,
    164: 36,
    165: 36,
    166: 30,
    167: 24, # section sign
    168: 30,
    169: 36, # copyright
    170: 30,
    171: 30,
    172: 30,
    173: 30,
    174: 36, # (r)
    175: 30,
    176: 30, # degree sign
    177: 30,
    178: 30,
    179: 30,
    180: 30,
    181: 30,
    182: 30,
    183: 30, # middle dot
}
