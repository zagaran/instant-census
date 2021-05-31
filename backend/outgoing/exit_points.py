#!/usr/bin/env
from time import sleep
from flask import flash
from werkzeug.contrib.cache import SimpleCache

from backend.outgoing.message_builder import merge_in_custom_attributes, preprocess_question,\
    check_for_problem_characters
from conf.settings import MONTHLY_MSG_USAGE_LIMIT, LIFETIME_MSG_USAGE_LIMIT,\
    BAD_RESPONSE_RESEND_QUESTION_APPEND
from constants.exceptions import TwilioDeliveryException
from constants.messages import PASSWORD_STRING
from database.analytics.responses import Response
from database.tracking.messages import ControlMessage, Message, Messages, ControlMessages
from utils.database import ID_KEY
from utils.logging import log_error
from utils.time import now
from utils.twilio_utils import twilio_send

""" broadcast message: for user in Users.active(): send_control_message(user, message) """

PRESEND_SLEEP = 5
CACHE = SimpleCache() #default timeout is 300 seconds

def over_usage_limit():
    """ Checks to see if a custoemr is over their total or monthly message usage limit """
    #TODO redo. this call is not performant. Remove for scalability
    if LIFETIME_MSG_USAGE_LIMIT:
        if Messages.count() >= LIFETIME_MSG_USAGE_LIMIT:
            CACHE.set("over_usage_limit", True)
            return True
    if MONTHLY_MSG_USAGE_LIMIT:
        cached_value = CACHE.get("over_usage_limit")
        if cached_value is not None:
            return cached_value
        # get current month
        curr_month = now().month
        # get latest MONTHLY_MSG_USAGE_LIMIT messages
        msgs = Messages(ascending=False, page_size=MONTHLY_MSG_USAGE_LIMIT)
        # get latest MONTHLY_MSG_USAGE_LIMIT control messages
        control_msgs = ControlMessages(ascending=False, page_size=MONTHLY_MSG_USAGE_LIMIT)
        # put together in one list
        all_messages = msgs + control_msgs
        # sort list in-place by time from latest message to earliest message
        all_messages.sort(key=lambda m: m['time'], reverse=True)
        # truncate list to latest MONTHLY_MSG_USAGE_LIMIT messages
        all_messages = all_messages[:MONTHLY_MSG_USAGE_LIMIT]
        # if there exists MONTHLY_MSG_USAGE_LIMIT messages and the earliest message in the latest MONTHLY_MSG_USAGE_LIMIT messages
        # has the same month date as current month, then admin is over the message limit
        if len(all_messages) == MONTHLY_MSG_USAGE_LIMIT and all_messages[-1]["time"].month == curr_month:
            CACHE.set("over_usage_limit", True, timeout=100)
            return True
        CACHE.set("over_usage_limit", False, timeout=1)
    return False

############################### EXIT POINTS #################################

def send_control_message(user, message_body, delay=True):
    if over_usage_limit():
        return
    if PASSWORD_STRING in message_body:
        message_body = message_body.replace(PASSWORD_STRING, user["temp_pass"])
    message_body = merge_in_custom_attributes(message_body, user=user)
    message_body = check_for_problem_characters(message_body)
    if delay:
        sleep(PRESEND_SLEEP)
    try:
        message = twilio_send(user, message_body)
    except TwilioDeliveryException:
        # stop execution of code because message was NOT sent and we shouldn't store it
        return
    try:
        message_sid = None
        if message:
            message_sid = message.sid
        ControlMessage.store(user, message_body, False, now(), message_sid)
    except Exception as e:
        log_error(e, "Failed to save outgoing text to database: " +
                  str(user[ID_KEY]) + " " + str(message_body))


def do_send_question(user, question, delay=True):
    if over_usage_limit():
        return
    processed_question_text = preprocess_question(user, question)
    processed_question_text = check_for_problem_characters(processed_question_text)
    if delay:
        sleep(PRESEND_SLEEP)
    try:
        twilio_message = twilio_send(user, processed_question_text)
    except TwilioDeliveryException:
        # stop execution of code because message was NOT sent and we shouldn't store it
        return
    try:
        send_time = now()
        period_start, schedule_id = Message.get_execution_info(user, True)
        message = Message.store_question_message(user, question[ID_KEY], processed_question_text, period_start, schedule_id, twilio_message.sid, send_time)
        Response.store(user, question, message, send_time, period_start, schedule_id)
    except Exception as e:
        log_error(e, "Failed to save outgoing question to database: " +
                  str(user[ID_KEY]) + " " + str(question))

def bad_response_resend_question(user, question_id, prepend_text, delay=True):
    if over_usage_limit():
        return
    if BAD_RESPONSE_RESEND_QUESTION_APPEND:
        last_question_text = "%s %s" % (prepend_text, user.last_question_message_text())
    else:
        last_question_text = prepend_text
    if delay:
        sleep(PRESEND_SLEEP)
    try:
        twilio_message = twilio_send(user, last_question_text)
    except TwilioDeliveryException:
        # stop execution of code because message was NOT sent and we shouldn't store it
        return
    try:
        send_time = now()
        period_start, schedule_id = Message.get_execution_info(user, True)
        message = Message.store_resend_message(user, question_id, last_question_text, period_start,
                                               schedule_id, twilio_message.sid, send_time)
        response = Response.retrieve(user[ID_KEY], question_id, period_start)
        response.store_bad_response_resend(message, send_time)
    except Exception as e:
        log_error(e, "Failed to save outgoing question to database: " +
                  str(user[ID_KEY]) + " " + str(question_id))

def non_response_resend_question(user, question_id, delay=True):
    if over_usage_limit():
        return
    last_question_text = user.last_question_message_text()
    if delay:
        sleep(PRESEND_SLEEP)
    try:
        twilio_message = twilio_send(user, last_question_text)
    except TwilioDeliveryException:
        # stop execution of code because message was NOT sent and we shouldn't store it
        return
    try:
        send_time = now()
        period_start, schedule_id = Message.get_execution_info(user, True)
        message = Message.store_resend_message(user, question_id, last_question_text, period_start, schedule_id,
                                               twilio_message.sid, send_time, is_question=True)
        response = Response.retrieve(user[ID_KEY], question_id, period_start)
        response.store_non_response_resend(message, send_time)
    except Exception as e:
        log_error(e, "Failed to save outgoing question to database: " +
                  str(user[ID_KEY]) + " " + str(question_id))
