def pack_range(bottom=None, top=None):
    range_string = ""
    if bottom:
        range_string += str(bottom)
    range_string += "~"
    if top:
        range_string += str(top)
    return range_string

# Note: range compare only works for ints right now
def range_compare(range_string, number):
    number = int(number)
    if "~" == range_string:
        return True
    if "~" not in range_string:
        return number == int(range_string)
    bottom, top = range_string.split("~")
    if bottom != "" and top != "":
        return int(bottom) <= number <= int(top)
    elif bottom != "":
        return int(bottom) <= number
    elif top != "":
        return number <= int(top)
    else:
        raise Exception("Malformed range object: " + range_string)


def parser_match(parsing, parser, match_range):
    '''returns true if there is a parser match in the parsing'''
    for tup in parsing:
        text, value, parser_name = tup
        if parser_name == parser and range_compare(match_range, value):
            return value
    return None
