from mongolia import ID_KEY

from backend.admin_portal.survey_builder_helpers import choices_append
from utils.time import datetime
from constants.database import ANSWER_VALUE
from database.backbone.schedules import (Schedule, Question, Conditional)
from database.backbone.cohorts import Cohort
from database.tracking.users import Users




def compile_survey(survey):
    # split survey into set of lines
    lines = survey.split("\n")
    # separate the header to create the schedule and isolate the cohort
    header = lines[0]
    schedule, cohort = parse_header(header)
    # create global user attributes
    if "attributes:" in lines[1]:
        #make line lower case in order to process attributes correctly
        line = lines[1].lower()
        attributes = line.split(": ")
        attributes = attributes[1].split("; ")
        attributes = parameter_parser((attributes))
        for key in attributes:
            Cohort(_id=cohort).add_custom_attribute(key, attributes[key])
            for user in Users(cohort_id=cohort):
                user.add_custom_attribute(key, attributes[key])
        lines = lines[1:]
    else: attributes = None
    # parse remaining lines of survey
    remaining = lines[1:]
    while remaining:
        remaining = parse(schedule, remaining, 0, cohort, attributes)

def parse_header(line):
    # this function parses the header and creates the schedule object
    # returns both the schedule object and the cohort id
    print("You have called the parse header function.")
    sections = line.split(": ")
    params = sections[1].split("; ")
    parameters = parameter_parser(params)
    sched = Schedule.create(parameters, random_id=True)
    return sched, parameters["cohort_id"]

def parameter_parser(line):
    # this function parses parameters divided by the equals sign and returns a dictionary
    # for lists, must conform to json (raise invalid json exception)
    print("You have called the parameter parser function.")
    param_dict = {}
    for x in line:
        parameter = x.split(" = ")
        for a, b in enumerate(parameter):
            if "[" and "]" in b:
                b = b.strip("[]")
                b = b.split(', ') #TODO: uh-oh commageddon! what about integers (though there shouldn't be)? things that do not have quotes?
                for i, x in enumerate(b):
                    x = x.strip('\'\"')
                    #print(x)
                    b[i] = x
                parameter[a] = b
            elif parameter[a] in ("true", "True"):
                parameter[a] = True
            elif parameter[a] in ("false", "False"):
                parameter[a] = False
            elif "20" and "-" in b:
                parameter[a] = convert_to_datetime(b)
            elif b.isdigit():
                parameter[a] = int(b)
        param_dict[parameter[0]] = parameter[1]
    # ensure that the cohort key in the dictionary is attached to the correct value
    if "cohort" in param_dict:
        param_dict['cohort'] = Cohort(cohort_name=param_dict['cohort'])[ID_KEY]
        param_dict['cohort_id'] = param_dict.pop('cohort')
    return param_dict

def convert_to_datetime(date_string):
    date_formatted = datetime.strptime(date_string, "%Y-%m-%d %M:%S:%f")
    return date_formatted


def parse_line(line, node, cohort, attributes):
    # parses lines in the survey in order to create questions, conditionals, and messages
    print("You have called the parse line function.")
    # first, formats text and divides the head (before the colon) and the rest of the text
    # information contained in the head indicates what sort of database object is to be created
    text = line.strip()
    if "{" in text:
        head, text = text.split("{")
        text = text.strip("}")
    else: head = text

    # create dictionary of kwargs found in the head (to be fed into database objects)
    if ": " in head:
        head = head.strip()
        parameters = head.split(": ")
        if "=" in head:
            parameters = parameters[1].split("; ")
            parameters = parameter_parser(parameters)
    else: parameters = {}

    if head.startswith("set attribute"):
        change_attribute(line, node, attributes)
        head = ""

    if "if" in head:
        if " attribute " in head:
            #separate string
            head = head.split("if attribute ")
            head = head[1].split(" is ")
            attribute, comparison = head[0], head[1]
            comparison = comparison.strip(":")
            #check if attribute in attributes
            if attributes is None:
                raise Exception ("You have an attribute in your survey syntax, but no attributes declared!")
            elif attribute not in attributes:
                raise Exception ("An attribute you are using is not declared in your survey!")
            conditional = Conditional.create({"cohort_id": cohort,
                                              "attribute": attribute,
                                              "comparison": comparison},
                                             random_id=True)
        else:
            if "yes" in head:
                comparison = "yes"
            elif "no" in head:
                comparison = "no"
            else:
                comparison = head.strip("if ")
                comparison = comparison.strip(":")
            conditional = Conditional.create({"cohort_id": cohort,
                                          "attribute": ANSWER_VALUE,
                                          "comparison": comparison},
                                         random_id=True)

        node.add_action("conditional", {"database_id": conditional[ID_KEY]})
        node = conditional
    else:
        if "question" in head:
            node = create_question(text, node, cohort, attributes, **parameters)
        elif "message" in head:
            node = create_message(text, node, attributes)
    return node

def create_question(text, node, cohort, attributes, **kwargs):
    # creates a question with parameters passed in via kwargs
    kwargs["cohort_id"] = cohort
    kwargs["text"] = text
    question = Question.create(kwargs,
                               random_id=True)
    node.add_action("send_question", {"database_id": question[ID_KEY]})
    if "auto_append" in kwargs and kwargs["auto_append"] == True:
        question.update(choices_append=choices_append(question))
    # returns the created question as the new node
    node = question
    return node

def change_attribute(text, node, attributes):
    # changes an existing attribute
    text = text.split("set attribute ")
    text = text[1].split(" to ")
    attribute_key, attribute_value = text[0], text[1]
    if attributes is None:
        raise Exception ("You have an attribute in your survey syntax, but no attributes declared!")
    elif attribute_key not in attributes:
        raise Exception ("An attribute you are using is not declared in your survey!")
    if attribute_value == "*answer":
        attribute_value = ANSWER_VALUE
    node.add_action("set_attribute", {"attribute_name": attribute_key, "attribute_value": attribute_value})


def create_message(text, node, attributes):
    # creates a message
    node.add_action("send_message", {"text": text})
    node = "message"
    return node

def parse(node, remaining, indent, cohort, attributes):
    # recursive function that parses each line of the survey
    # call parse_line on first line
    node = parse_line(remaining[0], node, cohort, attributes)
    remaining = remaining[1:]
    # parse according to whether the next line has the same indentation level
    while remaining:
        next_indent = get_indentation_level(remaining[0], indent)
        if next_indent <= indent:
            return remaining
        else:
            remaining = parse(node, remaining, indent + 1, cohort, attributes)

def get_indentation_level(line, current_indent):
    # determines indentation level of a given line in the survey text, assuming first line indent is 0
    n = len(line) - len(line.lstrip(" "))
    if n % 4 != 0:
        raise Exception("Your indentation sucks. Learn how to count in fours.")
    elif n > n + 4:
        raise Exception("Your thumb got stuck on the space bar.")
    elif "\t" in line:
        raise Exception("Please do not use any tabs, thank you very much.")
    return n / 4