from yes_or_no_parser import yes_or_no_parser
from number_parser import number_parser
from multiple_choice_parser import multiple_choice_parser
from email_parser import email_parser

PARSERS = {
    "open_ended": None,
    "multiple_choice_parser": multiple_choice_parser,
    "number_parser": number_parser,
    "yes_or_no_parser": yes_or_no_parser,
    "email_parser": email_parser,
}


class Parser(object):
    open_ended = "open_ended"
    multiple_choice_parser = "multiple_choice_parser"  # Multiple choice TODO: refactor multiple_choice_parser to be multiple choice
    number_parser = "number_parser"
    yes_or_no_parser = "yes_or_no_parser"
    email_parser = "email_parser"
