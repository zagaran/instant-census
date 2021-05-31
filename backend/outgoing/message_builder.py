import re
from mongolia import ID_KEY
from parsers.registry import Parser
from constants.parser_consts import CUSTOM_ATTRIBUTE_PARSE_PATTERN,\
    PROBLEM_CHARACTERS
from utils.logging import log_warning

def check_for_problem_characters(message_text):
    for char in PROBLEM_CHARACTERS:
        if char in message_text:
            message_text = message_text + u'\xa0'
            break
    return message_text
    
def merge_in_custom_attributes(message_text, user=None, cohort=None, testing=False):
    if user is None and cohort is None:
        raise Exception("merge_in_custom_attributes2() requires a User or Cohort to be passed in.")
    if "[[" not in message_text or "]]" not in message_text:
        # If not both "[[" and "]]" exist in message_text, we don't have to merge anything
        return message_text
    matches = re.findall(CUSTOM_ATTRIBUTE_PARSE_PATTERN, message_text)
    if not matches and not testing:  # Don't print if we're just testing merge to warn Admins
        # This should theoretically never be hit since we check for "[[" and "]]" earlier
        log_warning('No matches found in merge_in_custom_attributes() for message text: "%s"' % message_text)
    merged_message_text = message_text
    for match in matches:
        attribute_value = get_custom_attribute_value(match, user, cohort)
        merged_message_text = merged_message_text.replace(match, attribute_value)
    return merged_message_text
    

def get_custom_attribute_value(attribute_match, user, cohort):
    attribute = attribute_match[2:-2].strip().lower()  # The first and last two chars will be "[[" and "]]" from regex
    try:
        if user["custom_attributes"][attribute]:  # To catch cases where this might be empty string
            return user["custom_attributes"][attribute]
    except:
        pass
    try:
        return user.get_cohort()["custom_attributes"][attribute]
    except:
        pass
    try:
        return cohort["custom_attributes"][attribute]
    except:
        pass
    raise Exception('No custom attribute "%s"' % attribute)


def preprocess_question(user, question):
    question_text = question["text"]
    if "LAST_POLLED" in question_text:
        last_polled_time = user.last_polled_time(question[ID_KEY])
        # %A gives day of the week, %B gives the month, %d gives the day
        time_formatted = last_polled_time.strftime("%A %B %d")
        question_text = question_text.replace("LAST_POLLED", time_formatted)
    question_text = merge_in_custom_attributes(question_text, user=user)
    if question["parser"] == Parser.multiple_choice_parser and question['auto_append']:
        question_text += question["choices_append"]
    return question_text