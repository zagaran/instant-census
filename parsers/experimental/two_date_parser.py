from parsers import date_parser

def twodates(msg):
    first, second, add = "", "", 0
    if "between" in msg and "and" in msg:
        first = msg[:msg.index("and")]
        second, add = msg[msg.index("and"):], 5
    elif "from" in msg:
        if "to" in msg:
            first = msg[:msg.index("to")]
            second, add = msg[msg.index("to"):], 4
        if "until" in msg:
            first = msg[:msg.index("until")]
            second,add = msg[msg.index("until"):], 7
    return (date_parser(first)[0], date_parser(second)[0], date_parser(first)[1],
            date_parser(first)[2] + date_parser(second)[2] + add)