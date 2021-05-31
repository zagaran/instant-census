from datetime import timedelta
from flask.helpers import flash
import json
from mongolia.constants import ID_KEY
from threading import Thread

from bson import ObjectId

from backend.admin_portal.common_helpers import raise_400_error, raise_404_error
from backend.outgoing.message_builder import merge_in_custom_attributes
from conf.settings import DISABLE_LENGTH_RESTRICTION, ENABLE_FAST_FORWARD, ENABLE_SCHEDULE_TESTING
from constants.database import ANSWER_VALUE
from constants.parser_consts import FORBIDDEN_WORDS
from database.backbone.schedules import Schedule, Conditional, Question
from database.tracking.schedule_execution import ScheduleExecutions
from parsers.registry import PARSERS, Parser
from utils.actions import ActionConfig
from utils.formatters import convert_unicode
from utils.logging import log_error, log_thread
from utils.time import now
from constants.cohorts import ConditionalSubtype


def validate_schedule(schedule_id):
    # if invalid schedule_id
    if len(schedule_id) != 24:
        raise_404_error("Invalid Schedule ID.")
    # if schedule not found
    schedule = Schedule(ObjectId(schedule_id))
    if not schedule:
        raise_404_error("Schedule not found.")
    return schedule


def validate_and_unpack(data):
    #TODO: add validation for data
    try:
        unpacked_data = json.loads(data)
    except ValueError as e:
        log_error(e, "JSON decoding error")
        raise_400_error("Error: Malformed request.")
    # convert unicode
    for key in ["text", "comparison"]:
        if key in unpacked_data and unpacked_data[key]:
            unpacked_data[key] = convert_unicode(unpacked_data[key])
    if "choices_text" in unpacked_data and unpacked_data["choices_text"]:  # since this is in the form of a list
        unpacked_data["choices_text"] = [convert_unicode(text) for text in unpacked_data["choices_text"]]
    return unpacked_data


def validate_question_data(data):
    if "parser" not in data or data["parser"] not in PARSERS:
        raise_400_error("Invalid Question Type. You are attempting to create a question with an invalid type.")
    if not data["parser"]:
        data["parser"] = Parser.open_ended
    # check for min and max types must be int
    if "max" in data and not isinstance(data["max"], int):
        raise_400_error("Maximum allowed response to this numeric question is not a number.")
    if "min" in data and not isinstance(data["min"], int):
        raise_400_error("Minimum allowed response to this numeric question is not a number.")
    return data


def item_finder(item_id, item_type):
    if item_type == 'schedule':
        return Schedule(item_id)
    elif item_type == 'conditional':
        return Conditional(item_id)
    elif item_type in ['send_question', 'question']:
        return Question(item_id)
    return None


def add_to_parent(item_type, data, parent_id, parent_type):
    parent = item_finder(parent_id, parent_type)
    if parent is None:
        raise_400_error("You are attempting to create something attached to an invalid item.")
    parent.add_action(item_type, data)
    return True


def check_for_forbidden(data):
    if data['parser'] == 'multiple_choice_parser' and 'choices_text' in data:
        for x in data['choices_text']:
            x = x.lower().strip()
            if x in FORBIDDEN_WORDS:
                raise_400_error(
                    "Responses not allowed. You are attempting to create a question with reserved responses (e.g. 'STOP', 'START').")
    return False


def check_text(data, item_type):
    max_length = 160
    if DISABLE_LENGTH_RESTRICTION:
        max_length = 1600
    if item_type in ['send_message', 'send_question']:
        if len(data['text']) > max_length:
            raise_400_error(
                "Message too long. You are attempting to create a message longer than %s characters long." % max_length)


def check_attributes(data, cohort):
    if 'text' in data:
        try:
            merge_in_custom_attributes(data["text"], cohort=cohort, testing=True)
        except Exception as e:
            raise_400_error(str(e))
        if ("[[" in data["text"] or "]]" in data["text"]) and not ('[[' in data["text"] and "]]" in data["text"]):
            raise_400_error('There is an incorrectly formatted Custom Attribute insertion in your message: "%s"' % data["text"])
    return True

def recursive_attribute_check(node_object, cohort):
    attribute_dict = cohort['custom_attributes']
    error_message = 'Schedule cannot be copied. There is a Custom Attribute in the schedule that is not in the cohort %s.' % cohort['cohort_name']
    for action in node_object.actions:
        if action['action_name'] == "send_question":
            question = Question(action['action_id'])
            text = question['text']
            try:
                merge_in_custom_attributes(text, cohort=cohort)
            except:
                raise_400_error(error_message)
            recursive_attribute_check(question, cohort)
        elif action['action_name'] == "conditional":
            conditional = Conditional(action['action_id'])
            #check that the conditional attribute is NOT answer value while also checking if it exists in the new cohort
            if conditional['attribute'] != ANSWER_VALUE and conditional['attribute'] not in attribute_dict:
                raise_400_error(error_message)
            recursive_attribute_check(conditional, cohort)
        elif action['action_name'] == "set_attribute":
            params = action['params']
            if params['attribute_name'] not in attribute_dict:
                raise_400_error(error_message)
        elif action['action_name'] == "send_message":
            params = action['params']
            try:
                merge_in_custom_attributes(params['text'], cohort=cohort)
            except:
                raise_400_error(error_message)
    return True


def check_date(data, item_type):
    if item_type == 'schedule' and data['subtype'] == 'one_time':
        date = data['date']
        date = date.replace(hour=data['send_hour'])
        # Adds 1 day buffer for now to handle day passing in UTC to local time conversion
        if date < now() - timedelta(days=1):
            raise_400_error("You are attempting to create a One-Time Schedule for a date that has already passed.")
    return False


def update_database_object(item, data):
    if item is None:
        raise_400_error("You are attempting to update an item that does not exist. Try refreshing your page.")
    item.update(data)
    return "true"


def update_action(action_id, item_type, data, parent_id, parent_type):
    parent = item_finder(parent_id, parent_type)
    if parent is None:
        raise_400_error("You are attempting to update an invalid item.")
    for i, j in enumerate(parent.actions):
        if j['action_id'] == action_id:
            parent.actions[i] = ActionConfig.create_config(item_type, data, existing_id=action_id)
            parent.save()
    return "true"


def enact_move(item, index, switch):
    if item is None:
        raise_400_error("The item you are trying to move does not exist.")
    if switch < 0 or switch >= len(item.actions):
        return "true"
    item.actions[index], item.actions[switch] = item.actions[switch], item.actions[index]
    item.save()
    return "true"


def deleter(item, item_id, parent_id, parent_type):
    parent = item_finder(parent_id, parent_type)
    if item is None:
        raise_400_error("You are attempting to delete an item that does not exist.")
    if parent is None:
        raise_400_error("You are attempting to delete an improperly identified item.")
    remove_from_parent(parent, item_id)
    item.recursive_delete()
    return True


def remove_from_parent(parent, item_id):
    for i, j in enumerate(parent.actions):
        if j['action_id'] == item_id:
            del parent.actions[i]
            parent.save()
    return True


def choices_append(data):
    if data["parser"] == Parser.multiple_choice_parser:
        number_of_choices = int(data["choices"])
        choices_append = ""
        for counter, choice in enumerate(data["choices_text"]):
            # Add 1 to counter for comparisons because enumerate starts at 0
            if counter + 1 == number_of_choices and number_of_choices > 1:
                choices_append += " or %s?" % choice
            elif counter + 1 == number_of_choices:
                choices_append += " %s?" % choice
            else:
                choices_append += " %s," % choice
        return choices_append
    return ""

def update_conditionals(data, item):
    data_parser = data["parser"]
    conditionals = [item_finder(x["action_id"], "conditional") for x in item["actions"] if x["action_name"] == "conditional"]
    if data_parser != item["parser"] and data_parser != "open_ended":
        if data_parser == Parser.multiple_choice_parser:
            comparison = data["choices_text"][0]
            subtype = ConditionalSubtype.exactly
        elif data_parser == Parser.number_parser:
            comparison = str(data["min"])
            subtype = False
        elif data_parser == Parser.yes_or_no_parser:
            comparison = "yes"
            subtype = ConditionalSubtype.exactly
        for conditional in conditionals:
            conditional["comparison"] = comparison
            if subtype:
                conditional["subtype"] = subtype
            conditional.save()
    elif data_parser == Parser.multiple_choice_parser:
        if "choices_text" in data:
            for conditional in conditionals:
                if conditional["comparison"] not in data["choices_text"]:
                    conditional["comparison"] = data["choices_text"][0]
                    conditional["subtype"] = ConditionalSubtype.exactly
                    conditional.save()
    elif data_parser == Parser.number_parser:
        if "min" in data and "max" in data:
            for conditional in conditionals:
                if conditional["subtype"] == ConditionalSubtype.range:
                    minimum = conditional["comparison"]
                    maximum = conditional["upper_range"]
                    if int(minimum) < int(data["min"]):
                        minimum = data["min"]
                    if int(maximum) > int(data["max"]):
                        maximum = data["max"]
                    conditional["comparison"] = minimum
                    conditional["upper_range"] = maximum
                else:
                    comparison = int(conditional["comparison"])
                    if comparison < int(data["min"]):
                        conditional["comparison"] = str(data["min"])       
                    elif comparison > int(data["max"]):
                        conditional["comparison"] = str(data["max"])
                conditional.save()
    return True


def schedule_comparitor(a, b):
    #TODO: tests should be written
    """ Used to sort a list ordered from highest to lowest priority.
        Returns -1 if A is higher priority than B, or +1 if A is lower priority
        than B, since -1 means earlier in sort order. Returning 0 is equivalent to
        returning 1, which results in no switch."""
    # orders schedules by subtype
    SUBTYPE_PRIORITY = ["on_user_creation", "one_time", "recurring"]
    if SUBTYPE_PRIORITY.index(a["subtype"]) < SUBTYPE_PRIORITY.index(b["subtype"]):
        return -1
    if SUBTYPE_PRIORITY.index(a["subtype"]) > SUBTYPE_PRIORITY.index(b["subtype"]):
        return 1
    if SUBTYPE_PRIORITY.index(a["subtype"]) == SUBTYPE_PRIORITY.index(b["subtype"]):
        # orders schedules from earliest to latest scheduled, by 'date' and then 'send_time'
        if not a["date"] and not b["date"]:
            return 0
        elif not a["date"]:
            return 1
        elif not b["date"]:
            return -1
        else:
            if a["date"] < b["date"]:
                return -1
            if a["date"] > b["date"]:
                return 1
            if a["date"] == b["date"]:
                if a["send_hour"] < b["send_hour"]:
                    return -1
                if a["send_hour"] > b["send_hour"]:
                    return 1
    return 0    

def manually_run_schedule_core(schedule, cohort, curr_time):
    if not ENABLE_FAST_FORWARD:
        return
    # grab new schedules
    for user in cohort.get_active_users():
        user.update_schedule_executions(curr_time)
    # run executions for given schedule id
    for execution in ScheduleExecutions(schedule_id=schedule[ID_KEY]):
        thread = Thread(target=manually_run_schedule_execution, args=(execution, curr_time))
        thread.start()
        
def test_schedule_core(schedule, cohort, curr_time, users):
    if not ENABLE_SCHEDULE_TESTING:
        return
    for user in users:
        user.update_schedule_executions(curr_time)
        for execution in ScheduleExecutions(schedule_id=schedule[ID_KEY], user_id=user[ID_KEY]):
            thread = Thread(target=manually_run_schedule_execution, args=(execution, curr_time))
            thread.start()

@log_thread
def manually_run_schedule_execution(execution, curr_time):
    execution.update(execution_state=None, current_period_start=curr_time)
    execution.run(curr_time, manual_run=True)
