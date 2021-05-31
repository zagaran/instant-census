from constants.parser_consts import (NUMBER_WORDS, VALID_NUMERICS, ALPHANUMERICS,
                                     ILLEGAL_PUNCTUATION_COMBINATIONS,
    standard_punct, valid_number_parser_padding)


def number_parser(msg, question):
    """ Runs both the number parser and the word-number parser on the supplied
        text.  If a result is found in the number parser, the word-number parser
        is not run. """
    ret = parse_numerical_string(msg)
    if ret is not None:
        if question['min'] <= ret <= question['max']:
            return ret
        return None
    
    ret = parse_number_word(msg)
    if ret is not None:
        if question['min'] <= ret <= question['max']:
            return ret
        return None
    
    return None

################################################################################
###################### Fractions. Currently not implemented ####################
################################################################################

# def evaluate_fraction(fraction_string, debug):
#     """ Takes a numerical string with a slash (forward or backward) and returns
#         a float of the value of that fraction. """
#     numerator, denominator = fraction_string.split("/")
#     if not numerator:
#         debug += "\t bad numerator\n"
#         return None, debug
#     if not denominator:
#         debug += "\t bad denominator\n"
#         return None, debug
#     return float(numerator) / float(denominator), debug

################################################################################
######################### Numerical String Parsing #############################
################################################################################

def parse_numerical_string(text):
    """ Runs through the logic of checking each potential numerical substring
        for validity.  Returns the first such valid substring. """
    text = text.replace("\\", "/")
    candidates = []
    
    # Compose a list of potentially valid candidate numerical strings.
    for start, end in get_numeric_strings(text):
        substring = text[start:end]
        for char in standard_punct:
            substring.replace(char, "")
        if substring.strip() == "":
            continue  # Throw out whitespace lines
        if start > 0 and text[start - 1] not in valid_number_parser_padding + "$":
            continue  # Bad starting pad
        if end < len(text) and text[end] not in valid_number_parser_padding:
            continue  # Bad ending pad
        if check_invalid_punctuation_combos(substring):
            continue  # Throw out invalid punctuation
        candidates.append(substring.replace(",", ""))
    
    # Try to evaluate the candidate strings, return the first one that succeeds.
    for candidate in candidates:
        if candidate and candidate[-1] == ".":
            # remove a single trailing period
            candidate = candidate[:-1]
        try:
            return int(float(candidate))
        except ValueError:
            pass
    
    # No matches found
    return None

def get_numeric_strings(text):
    """ Runs through a string, pulling out the start and end index of potential
        strings of numerical sequences.  Returns a list of tuples of indexes. """
    start = -1
    end = -1
    ret = []
    for i in range(len(text)):
        if text[i] in VALID_NUMERICS:
            if start == -1:
                start = i
            end = i
            continue
        if start != -1:
            ret.append((start, end + 1))
        start = -1
    if end != -1 and start != -1:
        ret.append((start, end + 1))
    return ret


def check_invalid_punctuation_combos(text):
    """ Retuns True if there are any illegal punctuation strings on the string,
        otherwise returns False. """
    #this construction is slightly more efficient (smaller n) than
    # "for combo in ILLEGAL_PUNCTUATION_COMBINATIONS: check if in string."
    for i in range(0, len(text) - 1):
        if text[i:i + 2] in ILLEGAL_PUNCTUATION_COMBINATIONS:
            return True
    return False

################################################################################
################################ Number Words ##################################
################################################################################

def parse_number_word(text):
    """ Checks for matches in the text with the integers 0-20, returning that
        value as an int.  If it finds no matches it returns None, and if it finds
        multiple valid matches it returns None. """
    for word in extract_words(text):
        if word in NUMBER_WORDS:
            return int(NUMBER_WORDS[word])
    return None

def extract_words(text):
    """ Takes a string, returns a list of all the alphanumeric substrings. """
    text = text.lower()
    word = ""
    things = []
    for char in text:
        if char in ALPHANUMERICS:
            word += char
        elif word != "":
            things.append(word)
            word = ""
    if word != "":
        things.append(word)
    return things

################################################################################

#currently considered experimental, partially functional, imports are broken.

# makes sure that a word can be interpreted by text2int
# def is_numword(word):
#     return (word in numwords.keys() or word in ordinal_words or
#             word.endswith(("ieth", "rth", "nth", "dth")))

# Code of text2int from StackOverflow. Used under CC BY-SA.
# Original can be found at http://stackoverflow.com/a/598322
# takes a string of ONLY number words and converts them into an integer
# def text2int(textnum):
#     current = result = 0
#     tokens = re.split(r"[\s-]+", textnum) #split on whitespace or dashes...
#     for word in tokens:
#         if word in ordinal_words:
#             scale, increment = (1, ordinal_words[word])
#         else:
#             for ending, replacement in ordinal_endings:
#                 if word.endswith(ending):
#                     word = "%s%s" % (word[:-len(ending)], replacement)
#             if word not in numwords:
#                 raise Exception("Illegal word: " + word)
#             scale, increment = numwords[word]
#         if scale > 1:
#             current = max(1, current)
#         current = current * scale + increment
#         if scale > 100:
#             result += current
#             current = 0
#     return (result + current)

# catches numbers written as words
# def _textnum_parse(msg):
#     msg_words = split_standard_separators(msg)
#     textnum = ""
#     # find each word in the first textnum phrase
#     for word in msg_words:
#         if is_numword(word):
#             # catc the start index before continuing
#             if not textnum:
#                 start = msg.index(word)
#             textnum += word + " "
#         # once you start catching words that are not textnums, stop!
#         elif textnum:
#             break
#     textnum = textnum.strip()
#     # convert the text into digits
#     if textnum:
#         return str( text2int(textnum) )
#     else:
#         return None
