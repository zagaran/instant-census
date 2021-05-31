#!/usr/bin/python
# -*- coding: UTF-8 -*-

############################## Regex Strings ###################################
# Note: the characters in standard_punct and standard_delimiters CANNOT overlap.
from conf.settings import CUSTOM_START_WORDS
from constants.database import ANSWER_VALUE, SKIP_VALUE, BAD_RESPONSE_LIMIT_REACHED_VALUE

standard_punct = """!@#$%^&*"<>{}?()"""
standard_delimiters = r"""[-\s, ./;:\\|]"""
valid_number_parser_padding = standard_punct + standard_delimiters + """\r\n"""
# The standard_delimiters string is [correctly] formatted to match on whitespace,
# a colon, a semicolon, a comma, a period, a forward slash, a back slash, and a
# vertical bar when used with regex.

############################## Yes-No Lists ####################################

YES_LIST = set([
    'y',
    'yes',
    'yeah',
    'yea',
    'yeh',
    'yesh',
    'yep',
    'yup',
    'ya',
    'yah',
    'mhm',
    'mhmm',
    'sure',
    'fine',
    'alright',
    'alrite',
    'always',
    'correct',
    'affirmative',
    'ok',
    'okay',
    'okey',
    'dokey',
    'absolutely',
    'good',
    'true'
])

NO_LIST = set([
    'n',
    'no',
    'nope',
    'none',
    'not',
    'nah',
    'na',
    'never',
    'negative',
    'incorrect',
    'false'
])

############################ Lexical Number List ###############################
NUMBER_WORDS = {
    'zero': 0,
    'one': 1,
    'two': 2,
    'three': 3,
    'four': 4,
    'five': 5,
    'six': 6,
    'seven': 7,
    'eight': 8,
    'nine': 9,
    'ten': 10,
    'eleven': 11,
    'twelve': 12,
    'thirteen': 13,
    'fourteen': 14,
    'fifteen': 15,
    'sixteen': 16,
    'seventeen': 17,
    'eighteen': 18,
    'nineteen': 19,
    'twenty': 20
}

ALPHANUMERICS = set(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l',
                    'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x',
                    'y', 'z', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'])

############################ Character Sets ####################################
VALID_NUMERICS = set(["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ".", ","])

ILLEGAL_PUNCTUATION_COMBINATIONS = [',,', '.,', ',.', '..']
ILLEGAL_SLASHES = ['/, ', '\\, ', '/.', '\\.', './', '.\\', ', /', ', \\', '//', '/\\', '\\/', '\\\\']

# these characters have presented display problems on some devices
PROBLEM_CHARACTERS = [u"Á", u"á", u"À", u"à", u"Ä", u"ä", u"Â", u"â", u"Å", u"å",
                      u"Æ", u"æ",
                      u"É", u"é", u"È", u"è", u"Ë", u"ë", u"Ê", u"ê",
                      u"Í", u"í", u"Ì", u"ì", u"Ï", u"ï", u"Î", u"î",
                      u"Ó", u"ó", u"Ò", u"ò", u"Ö", u"ö", u"Ô", u"ô", u"Ø", u"ø",
                      u"Ú", u"ú", u"Ù", u"ù", u"Ü", u"ü", u"Û", u"û",
                      u"Ý", u"ý", u"Ỳ", u"ỳ", u"Ÿ", u"ÿ", u"Ŷ", u"ŷ",
                      u"Ç", u"ç",
                      u"Ñ", u"ñ",
                      u"ß"]

############################ Reserved Words ####################################
STOP_WORDS = ["stop", "stopall", "unsubscribe", "cancel", "end", "quit"]

#these words are equivalent to 'START'
START_WORDS = ['start', 'demo', 'hi', 'hello', 'begin'] + CUSTOM_START_WORDS

SYSTEM_WORDS = [ANSWER_VALUE, SKIP_VALUE, BAD_RESPONSE_LIMIT_REACHED_VALUE]

FORBIDDEN_WORDS = ['', 'ping', 'help', 'info'] + STOP_WORDS + START_WORDS + SYSTEM_WORDS

# parse pattern for parsing double bracketed attributes e.g. [[NAME]]
CUSTOM_ATTRIBUTE_PARSE_PATTERN = "\[\[.+?\]\]"

