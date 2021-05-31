import re


# EMAIL_ADDR_PATTERN =r"[^@]+@[^@]+\.[^@]+"
EMAIL_ADDR_PATTERN = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

def email_parser(msg):
    result = re.match(EMAIL_ADDR_PATTERN, msg)
    if not result:
        return None
    #else return email addr
    #FIXME: clean up whitespace, extract only email address
    return msg[result.start():result.end()]

