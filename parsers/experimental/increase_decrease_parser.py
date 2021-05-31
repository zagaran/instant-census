from constants.experimental_parser_consts.increase_decrease_list import DECREASE_LIST, INCREASE_LIST, STABLE_DICT
from utils.parser_helpers import split_string
from utils.decorators import Parser

@Parser
def increase_decrease_parser(msg):
    msg_words = split_string(msg, " ,.!?\/;")
    # find the words!  find them!!
    for word in msg_words:
        if word in INCREASE_LIST:
            return ("1", msg.index(word), msg.index(word) + len(word) - 1)
        elif word in DECREASE_LIST:
            return ("-1", msg.index(word), msg.index(word) + len(word) - 1)
        # check if the dictionary value in STABLE_DICT is in the msg
        elif word in STABLE_DICT and STABLE_DICT[word] and STABLE_DICT[word] in msg:
            return ("0", msg.index(STABLE_DICT[word]),
                        msg.index(STABLE_DICT[word]) + len(STABLE_DICT[word]) - 1)
        # if it's not, just check for words assigned to the value "None"
        elif word in STABLE_DICT and not STABLE_DICT[word]:
            return ("0", msg.index(word), msg.index(word) + len(word) - 1)
    return None
