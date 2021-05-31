from utils.database import DatabaseObject, DatabaseCollection, REQUIRED, ID_KEY
from utils.time import now
from mongolia.constants import REQUIRED_STRING
from utils.logging import log_warning

class RawMessage(DatabaseObject):
    PATH = "tracking.raw_messages"
    DEFAULTS = {
        "phonenum": REQUIRED_STRING,
        "text": REQUIRED_STRING,
        "ic_number": REQUIRED_STRING,
        "time": now,
        "twilio_message_sid": None
    }
    
    @staticmethod
    def store(phonenum, message, ic_number, receive_time, twilio_message_sid=None):
        return RawMessage.create({
            "phonenum": phonenum,
            "time": receive_time,
            "text": message,
            "ic_number": ic_number,
            "twilio_message_sid": twilio_message_sid
        }, random_id=True)

class RawMessages(DatabaseCollection):
    OBJTYPE = RawMessage


def diff_messages(ic_number):
    '''
        Outputs differences between RawMessage and Twilio message log for a specific ic_number
    '''
    from utils.server import get_twilio_client
    raw = RawMessages(ic_number=ic_number, field="text") + ControlMessages(ic_number=ic_number, field="text")
    t_log = []
    client = get_twilio_client()
    if client is None:
        return
    for m in client.sms.messages.iter(from_=ic_number):  # texts from us to user
        t_log.append(m.body)
    for m in client.sms.messages.iter(to=ic_number):  # texts from user to us
        t_log.append(m.body)
    print set(raw) ^ set(t_log)  # symmetric difference

class DroppedMessage(DatabaseObject):
    PATH = "tracking.dropped_messages"
    DEFAULTS = {
        "phonenum": REQUIRED_STRING,
        "text": REQUIRED_STRING,
        "ic_number": REQUIRED_STRING,
        "time": now,
        "twilio_message_sid": None
    }
    
    @staticmethod
    def store(phonenum, message, ic_number, receive_time, twilio_message_sid=None):
        return DroppedMessage.create({
            "phonenum": phonenum,
            "time": receive_time,
            "text": message,
            "ic_number": ic_number,
            "twilio_message_sid": twilio_message_sid
        }, random_id=True)


class DroppedMessages(DatabaseCollection):
    OBJTYPE = DroppedMessage


class ControlMessage(DatabaseObject):
    PATH = "tracking.control_messages"
    DEFAULTS = {
        "ic_number": REQUIRED_STRING,
        "incoming": False,
        "twilio_error_code": None, # if twilio_message_status is "failed" or "undelivered", will store twilio error code (https://www.twilio.com/docs/api/rest/message#error-values)
        "twilio_message_status": None, # stores twilio delivery receipts; not guaranteed to accurately reflect delivery status (https://www.twilio.com/docs/api/rest/message#sms-status-values)
        "twilio_message_sid": None, # twilio's unique message identifier
        "twilio_update_time": None, # timestamp of when most recent twilio callback is received
        "text": REQUIRED_STRING,
        "time": now,
        "user_id": REQUIRED,
    }
    
    @staticmethod
    def store(user, message, incoming, receive_time, twilio_message_sid=None):
        return ControlMessage.create({
            "user_id": user[ID_KEY],
            "time": receive_time,
            "text": message,
            "incoming": incoming,
            "ic_number": user["ic_number"],
            "twilio_message_sid": twilio_message_sid,
        }, random_id=True)

    @staticmethod
    def last_sent(user_id):
        return ControlMessages.get_last(sort_by="time", incoming=False, user_id=user_id)

class ControlMessages(DatabaseCollection):
    OBJTYPE = ControlMessage


class Message(DatabaseObject):
    PATH = "tracking.texts"
    # detail should be based on what the user specifies on the question object
    DEFAULTS = {
        "ic_number": REQUIRED_STRING,
        "incoming": False,
        "is_question": False,
        "needs_review": False,
        "parsing": None,
        "question_id": None,
        "schedule_id": None,
        "survey_period_start": None,
        "text": REQUIRED_STRING,
        "time": now,
        "twilio_error_code": None, # if twilio_message_status is "failed" or "undelivered", will store twilio error code (https://www.twilio.com/docs/api/rest/message#error-values)
        "twilio_message_status": None, # stores twilio delivery receipts; not guaranteed to accurately reflect delivery status (https://www.twilio.com/docs/api/rest/message#sms-status-values)
        "twilio_message_sid": None, # twilio's unique message identifier
        "twilio_update_time": None, # timestamp of when most recent twilio callback is received
        "user_id": REQUIRED,
    }
    
    @staticmethod
    def store_incoming(user, message, receive_time, needs_review, twilio_message_sid=None):
        period_start, schedule_id = Message.get_execution_info(user)
        return Message.create({
            "user_id": user[ID_KEY],
            "time": receive_time,
            "text": message,
            "incoming": True,
            "needs_review": needs_review,
            "ic_number": user["ic_number"],
            "schedule_id": schedule_id,
            "survey_period_start": period_start,
            "twilio_message_sid": twilio_message_sid
        }, random_id=True)
    
    @staticmethod
    def store_resend_message(user, question_id, question_text, period_start, schedule_id, twilio_message_sid,
                             send_time, is_question=False):
        """ param is_question: False for bad_response_resend, True for non_response_resend """
        return Message.create({
            "ic_number": user["ic_number"],
            "incoming": False,
            "is_question": is_question,
            "question_id": question_id,
            "schedule_id": schedule_id,
            "survey_period_start": period_start,
            "text": question_text,
            "time": send_time,
            "twilio_message_sid": twilio_message_sid,
            "user_id": user[ID_KEY],
        }, random_id=True)
    
    @staticmethod
    def store_question_message(user, question_id, processed_question_text, period_start, schedule_id, twilio_message_sid, send_time):
        return Message.create({
            "ic_number": user["ic_number"],
            "incoming": False,
            "is_question": True,
            "question_id": question_id,
            "schedule_id": schedule_id,
            "survey_period_start": period_start,
            "text": processed_question_text,
            "time": send_time,
            "twilio_message_sid": twilio_message_sid,
            "user_id": user[ID_KEY],
        }, random_id=True)
    
    @staticmethod
    def get_execution_info(user, execution_expected=False):
        from database.tracking.schedule_execution import ScheduleExecution
        current_execution = ScheduleExecution(user["current_execution"])
        if not current_execution:
            if execution_expected:
                log_warning("No execution exists for user %s while sending at %s" % (user[ID_KEY], now()))
            period_start = None
            schedule_id = None
        else:
            period_start = current_execution["current_period_start"]
            schedule_id = current_execution["schedule_id"]
        return period_start, schedule_id
    
    def append(self, additional_text):
        self["text"] += "\n\n" + additional_text
        self.save()

class Messages(DatabaseCollection):
    OBJTYPE = Message
