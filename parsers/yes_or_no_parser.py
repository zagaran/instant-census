from constants.parser_consts import NO_LIST, YES_LIST
from utils.parser_helpers import split_standard_separators, strip_standard_punct

def yes_or_no_parser(msg, question):
    """ Takes a message and returns a string containing 'yes' or 'no';
    Ensure you use proper truthiness evaluation"""
    
    msg = msg.lower()
    msg = strip_standard_punct(msg)
    msg_words = split_standard_separators(msg)
    
    yes = no = False
    for x in msg_words:
        x = x.strip()
        if x in YES_LIST and not yes:
            yes = True
        if x in NO_LIST and not no:
            no = True
    if yes and no:
        return None  # If they answered both yes and no, that is the same as not answering.
    if yes:
        return "yes"
    if no:
        return "no"
    
    return None
