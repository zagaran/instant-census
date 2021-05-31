from mongolia.constants import ID_KEY

from backend.outgoing.exit_points import do_send_question, send_control_message, non_response_resend_question
from constants.database import ANSWER_VALUE, SKIP_VALUE
from constants.users import Status
from database.backbone.schedules import Conditional, Question
from utils.actions import Action
from utils.formatters import encode_unicode
from utils.logging import log_warning, log_error
from constants.cohorts import ConditionalSubtype


@Action("set_attribute")
def set_attribute(user, attribute_name, attribute_value, parser_return=None):
    # Special case: if the value to set the attribute is ANSWER_VALUE", set the user's attribute to the return of the parser
    if attribute_value == ANSWER_VALUE:
        # don't set attribute if there's no valid parser_return value given (so that attribute remains unchanged)
        if parser_return is None:
            return
        # if user skipped this question, we don't want to change any values
        if parser_return == SKIP_VALUE:
            return
        attribute_value = parser_return
    # set status
    if attribute_name == "status":
        if attribute_value == Status.active:
            user.set_status(Status.active)
        elif attribute_value == Status.paused:
            user.set_status(Status.paused)
        elif attribute_value == Status.completed:
            user.set_status(Status.completed)
        else:
            log_error("Invalid value " + attribute_value + " for User Status change")
    # set attribute
    else:
        user["custom_attributes"][attribute_name] = attribute_value
        user.save()


@Action("send_message")
def send_message(user, text, delay=True):
    send_control_message(user, text, delay=delay)


@Action("send_question")
def send_question(user, database_id, parser_return=None, execution_state=[],
                  resend=False, delay=True):
    question = Question(database_id)
    if not question:
        log_warning("question %s does not exist" % database_id)
        return False

    #We are at the end of the action chain, and with resend == True should resend
    #the question rather than skipping to its actions
    if len(execution_state) == 1 and resend == True:
        non_response_resend_question(user, question[ID_KEY], delay=delay)
        return [question[ID_KEY]]
    # If we are operating off of a saved execution state, we are in the question's
    # actions list; do not send the question
    if execution_state:
        return question.do_actions(user, parser_return, execution_state,
                                   resend=resend, delay=delay)

    do_send_question(user, question, delay=delay)
    return [question[ID_KEY]]


@Action("conditional")
def conditional(user, database_id, parser_return=None, execution_state=[],
                resend=False, delay=True):
    conditional_obj = Conditional(database_id)
    subtype = conditional_obj["subtype"]
    if not conditional:
        log_warning("conditional %s does not exist" % database_id)
        return False

    # If we are operating off of a saved execution state, then the condition
    # was true at the point it was saved, so skip the condition check
    if execution_state:
        return conditional_obj.do_actions(user, parser_return, execution_state,
                                          resend=resend, delay=delay)

    # Special case: if attribute is ANSWER_VALUE, compare against answer
    if conditional_obj["attribute"] == ANSWER_VALUE and parser_return is not None:
        attribute = parser_return
    # Otherwise, compare against that user attribute
    else:
        attribute = user["custom_attributes"].get(conditional_obj["attribute"])        
    
    if conditional_obj["comparison_is_attribute"]:
        comparison = user["custom_attributes"].get(conditional_obj["comparison"])
        upper_range = user["custom_attributes"].get(conditional_obj["upper_range"])
    else:
        comparison = conditional_obj["comparison"]
        upper_range = conditional_obj["upper_range"]
    
    if isinstance(attribute, basestring):
        attribute = attribute.lower()
    
    # comp_range = conditional_obj["comparison"].split('-')
    # if len(comp_range) == 2:
    #     if int(comp_range[0]) <= int(comparison) <= int(comp_range[1]):
    #         return conditional_obj.do_actions(user, parser_return, delay=delay)
    if (subtype == ConditionalSubtype.exactly and 
        str(encode_unicode(attribute)) == str(encode_unicode(comparison)).lower()):
        return conditional_obj.do_actions(user, parser_return, delay=delay)
    try:
        comparison = float(comparison)
        attribute = float(attribute)
    except (ValueError, TypeError):
        return
    if subtype == ConditionalSubtype.greater and attribute > comparison:
        return conditional_obj.do_actions(user, parser_return, delay=delay)
    elif subtype == ConditionalSubtype.less and attribute < comparison:
        return conditional_obj.do_actions(user, parser_return, delay=delay)
    elif subtype == ConditionalSubtype.range:
        try:
            upper_range = float(upper_range)
        except (ValueError, TypeError):
            return
        if comparison <= attribute <= upper_range:
            return conditional_obj.do_actions(user, parser_return, delay=delay)


@Action("print_text")
def print_text(user, text):
    log_warning(text)
