# a few words about this bodypart parser:
# 1) meant to be more specific than sensitive (fewer false positives at the expense of missing words if they're misspelled)
# 2) sacrafices sensitivity for speed (by splitting the list up into strings)
# feel free to ask hannah what she means by all this

from constants.experimental_parser_consts import bodypart_list
from utils.parser_helpers import split_string
from utils.decorators import Parser

@Parser
def body_part_parser(msg):
    # splits the message up into a list of single words
    msg_words = split_string(msg, " ,.!?\/:;")
    # check if a word in the message is in the body parts list
    try:
        bodypart = next(word for word in msg_words if word in bodypart_list.order)
        start = msg.index(bodypart)
    except StopIteration:
        bodypart = None
    # check if word is part of a phrase
    if bodypart and bodypart_list.order[bodypart]:
        bodypart = next(phrase for phrase in bodypart_list.order[bodypart] if phrase in msg)
        start = msg.index(bodypart)
    # return contents or false (if empty)
    if bodypart:
        return (bodypart, start, start + len(bodypart) - 1)
    else:
        return None
