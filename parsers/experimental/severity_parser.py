#return is in form of (severity, start, finish)
from constants.experimental_parser_consts.severity_list import modifiers, severity_list
from utils.parser_helpers import split_string

# my algorithm for determining severity
# begins by taking in msg then looks for
# predefined severity descritions
# if it exists, then we look for adverbs that
# enhance severity

def severity_parser(msg):
    severity_score = None
    msg_words = split_string(msg, " ,.!?\/;")
    try:
        desc = next(desc for desc in severity_list if desc in msg_words)
    except StopIteration:
        return None
    start = msg.index(desc)
    for mod in modifiers:
        if mod in msg:
            start = msg.index(mod)
            if severity_score == None:
                severity_score = modifiers[mod]
            else:
                severity_score *= modifiers[mod]
    if severity_score == None:
        severity_score = severity_list[desc]
    else:
        severity_score = round (severity_score * severity_list[desc], 2)

    if severity_score >= 0:
        return (severity_score, start, msg.index(desc) + len(desc) - 1)
    else:
        return None
