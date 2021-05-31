from database.analytics.responses import Response, Responses
from utils.database import ID_KEY
from conf.settings import BAD_RESPONSE_RESEND_LIMIT
from database.tracking.messages import Messages, ControlMessages
from operator import itemgetter
from datetime import timedelta
from utils.logging import log_error
from utils.formatters import remove_unicode

class UserMessages(object):
    def all_messages(self, **kwargs):
        messages = Messages(user_id=self[ID_KEY], **kwargs)
        control_messages = ControlMessages(user_id=self[ID_KEY], **kwargs)
        return sorted(messages + control_messages, key=itemgetter("time"))
    
    def messages(self, **kwargs):
        return Messages(user_id=self[ID_KEY], **kwargs)
    
    def print_messages(self):
        last = None
        for message in self.all_messages():
            if last is None or message["time"].date() - last.date() >= timedelta(days=1):
                print(message["time"].strftime("\n%h %d, %Y"))
            last = message["time"]
            direction = "[in] " if message["incoming"] else "[out]"
            print("    %s %s: %s" % (message["time"].strftime("%H:%M:%S"), direction, message["text"]))
    
    def below_question_limit(self):
        #TODO: move to schedule_execution for daily_limit schedules
        #TODO: DO NOT USE CURRENT_PERIOD_START. TIMEZONE ADJUST BREAKS THIS.
        raise Exception
        limit = 2
        messages = Messages(sort_by="time", ascending=False, field="time", user_id=self[ID_KEY],
                            incoming=False, is_question=True, page_size=limit)
        if len(messages) < limit:
            return True
        try:
            return messages[-1] < self["current_period_start"]
        except IndexError:
            return True
    
    def last_polled_time(self, question_id):
        '''Given a question_id, returns the message object for the last time that question
        was sent to the user.'''
        last_message = Messages.get_last(sort_by='time', incoming=False,
                                         user_id=self[ID_KEY], is_question=True,
                                         question_id=question_id)
        if not last_message:
            # if twilio_update_time (timestamp for twilio callback status update) is None, return create_time
            return self["twilio_update_time"] or self["create_time"]
        return last_message["time"]
    
    def last_question_message_text(self):
        try:
            response = Responses.get_last(sort_by="original_send_time", user_id=self[ID_KEY],
                                      answer_value=None)
            return response.get_original_merged_question_text()
        except Exception as e:
            log_error(e, "No Response object found for get_last_unanswered_question_text for user %s." % self)
    
    def last_received(self):
        return Messages.get_last(sort_by='time', incoming=True, user_id=self[ID_KEY])

    def last_sent(self):
        return Messages.get_last(sort_by="time", incoming=False, user_id=self[ID_KEY])

    def can_resend(self, limit=BAD_RESPONSE_RESEND_LIMIT):
        """ If at least one the last N messages sent to the user are questions
            (is_question=True), then the user can receive a resend """
        if BAD_RESPONSE_RESEND_LIMIT == 0:
            return False
        return any(Messages(sort_by="time", user_id=self[ID_KEY], incoming=False,
                            ascending=False, page_size=limit, field="is_question"))

    def print_executions(self):
        from database.tracking.schedule_execution import ScheduleExecutions
        print "------------"
        print "USER ID:"
        print self[ID_KEY]
        print "------------"
        print "ACTIVE:"
        for execution in ScheduleExecutions(user_id=self[ID_KEY], active=True):
            self.print_execution(execution)
        print "------------"
        print "INACTIVE:"
        for execution in ScheduleExecutions(user_id=self[ID_KEY], active=False):
            self.print_execution(execution)
        print "------------"

    def print_execution(self, execution):
        from database.backbone.schedules import Schedule, Question
        schedule = Schedule(execution["schedule_id"])
        if not schedule:
            return
        print "\t------------"
        print "\t%s to %s" % (execution["current_period_start"], execution["current_period_end"])
        print "\tState: %s" % execution["execution_state"]
        print "\tResends: %s" % [str(t) for t in execution["resend_times"]]
        print "\tSchedule: %s (id %s)" % (schedule["subtype"], schedule[ID_KEY])
        for action in schedule["actions"]:
            if action["action_name"] == "send_question":
                question = Question(action["params"]["database_id"])
                if question:
                    print remove_unicode("\t\t%s %s" % (action["action_name"], question["text"]))
                else:
                    print "\t\t%s %s" % (action["action_name"], "ERROR")
            else:
                print remove_unicode("\t\t%s %s" % (action["action_name"], action["params"]))
