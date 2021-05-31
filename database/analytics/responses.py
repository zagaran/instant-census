from mongolia import DatabaseObject, REQUIRED, DatabaseCollection, ID_KEY
from mongolia.constants import REQUIRED_STRING
from utils.logging import log_warning, log_error
from utils.time import total_seconds


class Response(DatabaseObject):
    PATH = "tracking.responses"

    #user id, question id, survey_period start uniquely identifies Response object
    DEFAULTS = {
        "ic_number": None,
        "user_id": REQUIRED,
        "cohort_id": REQUIRED,
        "schedule_id": None,
        "question_id": REQUIRED,
        "question_subtype": None,
        "survey_period_start": REQUIRED,  # survey_period_start, abstract schedule time
        "question_text": REQUIRED_STRING,
        "original_send_time": REQUIRED,  # send time the question actually sent out
        "non_response_resend_times": [],  # list of timestamps of outgoing non-response prompted resends
        "bad_response_resend_times": [],  # list of timestamps of outgoing bad response prompted resends
        "times_of_responses": [],  # list of timestamps for all incoming messages
        "message_ids": [],  # list of all outgoing and incoming messages
        "response_time": None,  # how long it takes for first interaction, regardless if it answers the question
        "total_response_time": None,  # total response time including clarifications to answer the question
        "answer_value": None,  # the designated answer value of the response
    }
    
    @classmethod
    def store(cls, user, question, message, send_time, survey_period_start, schedule_id):
        # created during initial question send
        if Responses.count(user_id=user[ID_KEY], question_id=question[ID_KEY], survey_period_start=survey_period_start) > 0:
            log_warning(("Response object was found when none should exist for User:\n%s\n\n" % user +
                         "Question:\n%s\n\n" % question +
                         "Message:\n%s\n\n" % message +
                         "schedule_id: %s" % schedule_id))
            return None
        return Response.create({
                "ic_number": user["ic_number"],
                "user_id": user[ID_KEY],
                "cohort_id": user["cohort_id"],
                "schedule_id": schedule_id,
                "question_id": question[ID_KEY],
                "question_subtype": question["parser"],
                "survey_period_start": survey_period_start,
                "question_text": question["text"],
                "original_send_time": send_time,
                "message_ids": [message[ID_KEY]]
                }, random_id=True)
    
    @staticmethod
    def retrieve(user_id, question_id, survey_period_start):
        # should only be one
        response = Responses(user_id=user_id, question_id=question_id, survey_period_start=survey_period_start)
        if len(response) == 0:
            log_warning(("No Response object found in Response.retrieve call: " +
                         "user_id=%s; question_id=%s; survey_period_start=%s") % \
                        (user_id, question_id, survey_period_start))
        if len(response) > 1:
            log_warning(("Multiple Response objects found Response.retrieve call when only one expected: " +
                         "user_id=%s; question_id=%s; survey_period_start=%s") % \
                        (user_id, question_id, survey_period_start))
            return response[0]
        if len(response) == 1:
            return response[0]
        return None

    def update_response(self, message, receive_time, parser_return):
        self["message_ids"].append(message[ID_KEY])
        self["times_of_responses"].append(receive_time)
        # set response time if not already
        if not self["response_time"]:
            question_send_time = self["original_send_time"]
            if self["non_response_resend_times"]:
                question_send_time = self["non_response_resend_times"][-1]
            time_difference = receive_time - question_send_time
            response_time = total_seconds(time_difference)
            self["response_time"] = response_time
        # if a response in the expected format is given
        if parser_return is not None:
            # set answer_value
            self["answer_value"] = parser_return
        # set total response_time
        time_difference = receive_time - self["original_send_time"]
        total_response_time = total_seconds(time_difference)
        self["total_response_time"] = total_response_time
        self.save()

    def store_non_response_resend(self, message, receive_time):
        self["message_ids"].append(message[ID_KEY])
        self["non_response_resend_times"].append(receive_time)
        self.save()

    def store_bad_response_resend(self, message, receive_time):
        self["message_ids"].append(message[ID_KEY])
        self["bad_response_resend_times"].append(receive_time)
        self.save()

    def get_original_merged_question_text(self):
        from database.tracking.messages import Message
        return Message(self["message_ids"][0])["text"]

    def get_user_phone_number(self):
        from database.tracking.users import User
        return User(self["user_id"])["phonenum"]

class Responses(DatabaseCollection):
    OBJTYPE = Response

