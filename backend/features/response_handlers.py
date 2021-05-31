from backend.outgoing.dispatcher import (send_crisis_message,
    send_stop_word_in_message)
from backend.outgoing.exit_points import bad_response_resend_question, send_control_message
from conf.settings import BAD_RESPONSE_RESEND_LIMIT
from constants.database import BAD_RESPONSE_LIMIT_REACHED_VALUE
from constants.users import Status
from utils.database import ID_KEY
from constants.parser_consts import STOP_WORDS, START_WORDS
from backend.incoming.new_user import onboard_user
from utils.formatters import parser_format
from utils.parser_helpers import split_standard_separators
from utils.logging import log_warning
from backend.admin_portal.user_managment_helpers import send_status_message
from utils.time import now


def control_message_handler(user, msg):
    message_words = split_standard_separators(msg)
    if msg in STOP_WORDS:
        user.set_status(Status.disabled)
    elif "stop" in message_words:
        send_stop_word_in_message(user, "stop")
    elif "remove" in message_words:
        send_stop_word_in_message(user, "remove")
    elif msg in START_WORDS:
        if user["status"] == Status.inactive:
            user.set_status(Status.active)
            send_status_message(user)
        elif user["status"] == Status.pending:
            if user.get_cohort()["enableable_from_sms"]:
                user.set_status(Status.active)
                onboard_user(user, now(), delay=True)
            else:
                pass
                # TODO
        elif user["status"] == Status.disabled:
            # get status log reversed (most recent first)
            status_log = list(reversed(user["status_log"]))
            # set to most recent status that isn't disabled or inactive
            new_status = next((entry[0] for entry in status_log if entry[0] not in [Status.disabled, Status.inactive, Status.pending]), False)
            if not new_status:
                raise Exception("Exception raised in control_message_handler for this user: %s, cohort: %s, msg: %s, status log: %s" % (
                                user.phonenum,
                                user.get_cohort().cohort_name,
                                msg,
                                ",".join(list(user["status_log"]))))
            user.set_status(new_status)
        else:
            # Doesn't process "Start" if it doesn't trigger a status change
            return False
    elif msg == "help" or msg == "info":
        log_warning("Unexpected message forward from twilio: %s" % msg)
    elif msg == "ping":
        send_control_message(user, "pong", delay=False)
    else:
        return False
    return True


def crisis_message_handler(user, msg):
    keywords = ["suicide", "suicidal", "kill myself", "want to die", "wanna die"]
    for keyword in keywords:
        if keyword in msg:
            send_crisis_message(user)
            # mark as needs review
            user.update(needs_review=True)
            return True
    return False


def invalid_response_handler(user, last_question, message, response, delay=True):
    # mark as needs review
    user.update(needs_review=True)
    message.update(needs_review=True)
    resend = last_question["resend"]
    choices_append = last_question["choices_append"] if last_question["auto_append"] is False else ""
    if not resend:
        return False
    # resend question if not past BAD_RESPONSE_RESEND_LIMIT
    if user.can_resend(limit=BAD_RESPONSE_RESEND_LIMIT):
        bad_response_resend_question(user, last_question[ID_KEY], resend, delay=delay)
        return True
    # send out Cohort problem message if set
    if user.get_cohort()["problem_message"] is not None:
        send_control_message(user, user.get_cohort()["problem_message"], delay=delay)
    # set Response object answer value
    response.update(answer_value=BAD_RESPONSE_LIMIT_REACHED_VALUE)
    return False


def unsolicited_message_handler(user, message):
    # if this is the user's first message and it's "start", do not flag as needs review
    if len(user.all_messages()) == 1 and parser_format(message.text) in START_WORDS:
        pass
    # mark as needs review
    else:
        user.update(needs_review=True)
        message.update(needs_review=True)
    resp = user.get_cohort()["free_report_response"]
    if resp is None:
        return False
    if not user.is_active() or not user.cohort_is_active():
        return False
    send_control_message(user, resp)
    return True
