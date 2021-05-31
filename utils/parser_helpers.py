import re
from constants.parser_consts import standard_delimiters, standard_punct
########################### Precompiled Regexes ################################
STANDARD_SPLITTER = re.compile(standard_delimiters)
WHITESPACE_MATCH = re.compile('\s')
LOWERALPHAS = re.compile("[a-z]")

# def split_string(text, separators):
#     """ Splits input text at the instance of all the supplied separators.
#         To avoid confusion when entering your list of separators you should
#         supply it as a raw string (declare your string with a preceding 'r', similar too
#         declaring a unicode string), see below on note for backslashes.
#     
#     Python handles strings with backslashes Very strangely.  If you want to
#     include the backslash as a separator you must include it as either a regular
#     string with four backslashes in a row, or use a raw string with a double
#     backslash in it.  This is occurs because the regex module interprets
#     the supplied string of delimiters"""
#     reg = re.compile(separators)
#     return reg.split(text)

def split_standard_separators(text):
    """ Returns a list of words, retaining order, splitting on the following:
        whitespace, a colon, a semicolon, a comma, a period, a forward slash,
        and a back slash.
        Purges list of empty string elements. """
    return [x for x in STANDARD_SPLITTER.split(text) if x != ""]

def strip_standard_punct(text):
    """ Removes punctuation from the supplied string. The punctuation removed
    with this function does not overlap with any of the separator characters."""
    #could be implemented with regex, but trying to reduce use of regex
    for punct in standard_punct:
        text = text.replace(punct, "")
    return text

# def strip_punct_and_seperators(text):
#     for punct in standard_punct:
#         text = text.replace(punct, "")
#     for delimiter in standard_delimiters:
#         text = text.replace(delimiter, "")
#     return text

# exception check
def exception(exceptions, brand, text):
    for e in exceptions:
        if (brand in e) and (e in text):
            return True
    return False
