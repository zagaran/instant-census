from dateutil.parser import parse
from utils.decorators import Parser
from string import digits

def parse_time(s):
    if not s:
        return None
    for char in s:
        if char in digits:
            break
    else:
        return None
    try:
        return parse(s, fuzzy=False)
    except (ValueError, TypeError):
        return None

@Parser
def time_parser(msg):
    msg = msg.rstrip()
    for start in range(len(msg)):
        for end in range(len(msg), 0, -1):
            if parse_time(msg[start:end]):
                return ((parse_time(msg[start:end]), start, end - 1))
    return None
