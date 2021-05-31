from datetime import timedelta
from mongolia.constants import ID_KEY
from time import sleep

from backend.admin_portal.user_managment_helpers import send_status_message
from backend.features.response_handlers import (invalid_response_handler,
    unsolicited_message_handler)
from backend.features.schedule_features import run_outstanding_schedules
from backend.outgoing.dispatcher import send_inactive_message
from constants.database import SKIP_VALUE
from constants.users import Status
from database.analytics.responses import Response
from database.analytics.system_load import ResponseTime
from database.backbone.schedules import Schedule
from database.tracking.schedule_execution import ScheduleExecution
from parsers.registry import PARSERS, Parser
from utils.formatters import parser_format
from utils.logging import log_error, log_warning
from utils.parser_helpers import strip_standard_punct, split_standard_separators
from utils.time import now


def handle_message(user, curr_time, message, formatted_message, raw_message, delay):
    ########################### 'UNSOLICITED MESSAGE' BLOCK ###########################
    # If message is 'unsolicited' i.e without a question:
    # if there is no current outstanding question, this is an unsolicited message
    #user.is_active is to check of user's cohort is paused
    if not user["current_execution"] or not user.is_active() or not user.cohort_is_active():
        if unsolicited_message_handler(user, message):
            pass  # Continue execution
        return


    ############################ 'SOLICITED MESSAGE' BLOCK ##############################
    # If message is a response to a question, update appropriate database objects:
    execution = ScheduleExecution(user["current_execution"])
    if not execution:
        message.update(needs_review=True)
        user.update(needs_review=True)
        user.print_executions()
        raise Exception("Unexpected: user['current_execution'] points to an invalid/nonexistent " +
                        "execution at %s with message: %s" % (curr_time, raw_message))
    question = execution.get_question()
    if not question:
        message.update(needs_review=True)
        user.update(needs_review=True)
        user.print_executions()
        raise Exception("Unexpected: No question found for current execution for user " +
                        "%s at %s with message: %s" %
                        (user["phonenum"], curr_time, raw_message))

    # runs parsers on message
    parser_return = parse_text(formatted_message, question)
    # next two lines: if the question is open-ended, we want to store the not-parser-formatted message
    # as attribute, especially if execution involves a set_attribute
    if parser_return != SKIP_VALUE and question["parser"] == Parser.open_ended:
        parser_return = parser_format(raw_message, lower_caps=False, sub=False)

    # updates message with parser_return
    message.update(parsing=parser_return, question_id=question[ID_KEY],
                   schedule_id=execution["schedule_id"],
                   survey_period_start=execution["current_period_start"])

    # stores response time of user
    #TODO: remove and replace with Response.update when ready
    ResponseTime.store(user, message, question)

    # updates response object
    response = Response.retrieve(user[ID_KEY], question[ID_KEY], execution["current_period_start"])
    if not response:
        message.update(needs_review=True)
        user.update(needs_review=True)
        user.print_executions()
        raise Exception("Unexpected: No response found for user: %s, question: %s, execution: %s, with message: %s, at time %s." %
                        (user[ID_KEY], question[ID_KEY], execution[ID_KEY], raw_message, curr_time))
    response.update_response(message, curr_time, parser_return)

    #####################################################################################
    # DEPRECATED CODE:
    # If multipart message:
    # If message is exactly 160, wait for potential next part
    # TODO: This code does't work; multipart messages come in as 153 chars
    # because of headers (or different lengths entirely if they include unicode)
    #if delay and len(raw_message) == SMS_LENGTH:
    #    sleep(15) 
    # TODO: replace this with logic that waits if parser_return is none for a
    # subsequent message beginning with "*"
    #if delay and not parser_return.fully_parsed() and question.resend is None: sleep(30)


    ############################ 'INVALID RESPONSE' BLOCK ###############################
    # If invalid response i.e. parsers could not parse an answer:
    # if there is no parsed text (say, invalid multiple choice answer)
    if parser_return is None:
        # will return True if and only if it resends the question
        if invalid_response_handler(user, question, message, response, delay=delay):
            return


    ############################ 'RESPONSE ACCEPTED' BLOCK ##############################
    # RUN NEXT ACTION IN EXECUTION
    # TODO: Only send new question if it is safely before the end of a user's next schedule
    # TODO: maybe think of schedules more as adding something to a queue
    # if now() < user["current_period_end"] - timedelta(minutes=10):
    if execution.run(curr_time, parser_return=parser_return, delay=delay):
        return


    ###########################  'RUN NEXT EXECUTION' BLOCK #############################
    # If last execution completed, run next outstanding executions (uncompleted schedules)
    run_outstanding_schedules(user, curr_time, delay=delay)


###########################################################################################################
###########################################################################################################
###########################################################################################################

def parse_text(message, question):
    if check_for_skip(message):
        return SKIP_VALUE
    parser_name = None
    if question:
        parser_name = question["parser"]
    if parser_name == None or parser_name == Parser.open_ended:
        return message
    parser = PARSERS[parser_name]
    try:
        parsed_text = parser(message, question)
        if parsed_text is not None:
            return unicode(parsed_text)
        return None
    except Exception as e:
        log_error(e, "ERROR running parser " + str(parser))


def check_for_skip(msg):
    msg = msg.lower()
    msg = strip_standard_punct(msg)
    msg_words = split_standard_separators(msg)
    if msg_words and msg_words[0] == 'skip':
        return True
    return False


def inactive_user(user):
    inactive_limit = user.get_cohort()["inactive_limit"]
    inactive_time_limit = user.get_cohort()["inactive_time_limit"]
    if not inactive_limit and not inactive_time_limit:
        return False
    recent_messages = user.messages(ascending=False, page_size=inactive_limit)
    if user.last_sent():
        inactive_time = user.last_sent()["time"] + timedelta(hours=inactive_time_limit)
    else:
        inactive_time = user["create_time"] + timedelta(hours=inactive_time_limit)
    last_status, status_set_time = user.status_log[-1]
    if last_status != Status.active:
        log_warning('Non-Active Last Status Detected')
    # Recent_messages is a boolean and True == 1; so, if the incoming value of all recent
    # messages is False, and the user has been sent at least as many questions as
    # the inactive limit, and the user's most recent status change was before the
    # oldest of the recent messages, set them to inactive
    if (inactive_limit
        and sum(1 for i in recent_messages if i['incoming']) == 0
        and len(recent_messages) == inactive_limit
        and status_set_time < recent_messages[-1]['time']):
        user.set_status(Status.inactive)
        send_inactive_message(user)
        return True
    if (inactive_time_limit
        and inactive_time <= now()):
        user.set_status(Status.inactive)
        send_inactive_message(user)
        return True
    return False


def reactivate_user(user):
    if user["status"] == Status.inactive:
        if not user.get_cohort()["reactivate_allowed"]:
            return False
        user.set_status(Status.active)
        send_status_message(user)
        return True
    return False
