#!/usr/bin/python
# -*- coding: UTF-8 -*-
from mongolia import ID_KEY

from app import app
from backend.admin_portal.survey_builder_helpers import manually_run_schedule_core
from backend.incoming.entry_points import on_receive, every_hour_core
from backend.incoming.new_user import onboard_user
from backend.outgoing.message_builder import check_for_problem_characters
from constants.database import TEST_COHORT_PHONENUM
from constants.messages import MULTIPLE_CHOICE_RESEND_TEXT
from database.backbone.cohorts import Cohort
from database.backbone.schedules import Schedules
from database.tracking.schedule_execution import ScheduleExecutions
from database.tracking.users import User
from supertools.survey_reader import compile_survey
from tests.common import InstantCensusTestCase, test_admin_log_in_response, \
    create_new_cohort_response, copy_survey_to_cohort_response
from utils.time import now, timedelta, datetime, zero_day, convert_to_utc


QUESTION1 = "Is this the first question?"
QUESTION2 = "Is this another question?"
QUESTION3 = "Is this the third question?"
QUESTION4 = "This is a question for a on_user_creation schedule."
QUESTION_MULTIPLE_CHOICE = "Multiple choice question."
QUESTION_FOR_S7 = "this is a question for schedule 7"
SURVEY8_CHOICES = ["red", "blue", "green"]
SURVEY8_SECOND_CHOICES = ["red", "green"]
UNICODE_QUESTION1 = u"Wot a lovely first question, innit?"
UNICODE_QUESTION2 = u"Oh, did you want something with accênts? $¥mßΩls?¡"
UNICODE_MESSAGE = u"I thought so. Have an umbrella. ☂"

# These are configured times of schedules
ONE_TIME_START = datetime(2015, 1, 15, 19)
CONDITIONAL_SCHEDULE_START = datetime(2015, 2, 16, 18)
TIMEZONE_SCHEDULE_START = datetime(2015, 3, 1, 11)
MULTIPLE_CHOICE_START = datetime(2015, 4, 15, 14)
CURR_TIME = now() #TODO: how is time handled throughout the codebase?
SURVEY7_START = datetime(2015, 1, 15, 21)
SURVEY8_START = datetime(2015, 1, 15, 22)
SURVEY9_START = datetime(2015, 1, 15, 17)
SURVEY10_START = datetime(2015, 1, 15, 16)
SURVEY11_START = datetime(2015, 1, 15, 15)
SURVEY12_START = datetime(2015, 1, 15, 14)
SURVEY13_START = datetime(2015, 1, 15, 13)


CHOICES_MULTIPLE_CHOICE = ["$kL9#'a]<", "IGNOREME", "IGNOREMETOO"]
#Lists must not have commas in the individual items


################################################################################
######################         HOW TO WRITE SURVEYS         ####################
################################################################################

# 1. Use triple quotes on either side of your survey.
# 2. Begin with "header: ". The header will be the first line of your survey string, and it must
#    not contain any new lines or indentation. What the header should contain is any parameters
#    you would like to pass to the schedule.create() function. Beginning your header with
#    "cohort = __Test__;" is strongly recommended.
# 3. Parameters in the header, like all parameters in your survey string, should be written as
#    follows: "parameter_key = parameter_value". Use an equals sign to separate keys and values,
#    and use a semicolon to separate parameters (see existing surveys for examples).
# 4. Every question and conditional in your survey should constitute its own line.
# 5. INDENTATION MATTERS. DO NOT USE TABS. Signify dependencies by indenting four spaces on the
#    following line.
# 6. How to write questions:
#    a) Start with "question", which may be followed by a number (optional).
#    b) If including parameters, separate your parameters (which should be formatted in accordance
#       with (3) above) from "question[ n]" with a colon.
#    c) The text of the question should be encapsulated in curly brackets {} with NO quotation marks.
#       This should follow the "question" marker and any parameters.
# 7. How to write conditionals:
#    a) Conditionals generally consist of two lines. The first line establishes a dependency in one
#       direction (e.g. "if yes" or "if no"), positive or negative, the second in the opposite direction.
#       Begin a conditional on a new line with four more indents beginning the line.
#    b) The general syntax for a yes-no conditional: "if yes:" and "if no:"
#    c) For a multiple-choice/other answer conditional: "if [answer you'd like]:" is the correct format.
#    d) Any questions or messages subordinate to a conditional must be written on the line below the
#       "if..." statement and indented a further four spaces.
# 8. How to write messages:
#    a) Start with "message", which may be followed by a number or label (optional).
#    b) The text of the message should be in curly brackets {} following the "message" marker.
# 9. Using attributes:
#    a) Attributes in conditionals: The correct syntax for creating a dependency related to an
#       attribute is "if attribute color is purple:". All other rules of conditionals apply here
#       (this should be its own separate line).
#    b) Setting attributes: The correct syntax for setting an attribute is "set attribute color to
#       purple". There is no punctuation, and "set attribute" must be how the string begins. To set
#       an attribute to an answer, use the format "set attribute color to *answer". Don't forget the
#       asterisk.
#    c) An attribute written within a question or message text: surround it with double brackets and
#       all-caps, like [[BLUE]], within your string that is curly-bracketed.
#    d) Don't all-caps your attributes in your attribute declaration line, please. Resist the temptation.

survey1 = """header: cohort = __Test__; subtype = recurring; send_hour = 12; resend_hour = 14; resend_quantity = 5; question_period = 7
question 1 {%s}
question 2 {%s}""" % (QUESTION1, QUESTION2)

survey2 = """header: cohort = __Test__; subtype = one_time; send_hour = %s; date = %s
message {%s}""" % (ONE_TIME_START.hour, zero_day(ONE_TIME_START), QUESTION3)

survey3 = """header: cohort = __Test__; subtype = one_time; send_hour = %s; date = %s
question 1 {%s}""" % (TIMEZONE_SCHEDULE_START.hour, zero_day(TIMEZONE_SCHEDULE_START), QUESTION3)

survey4 = """header: cohort = __Test__; subtype = on_user_creation
question 1 {%s}""" % (QUESTION4)

survey5 = """header: cohort = __Test__; subtype = one_time; send_hour = %s; date = %s
question 1: parser = yes_or_no_parser {Answer YES}
    if yes:
        question 2: parser = yes_or_no_parser {Answer NO}
            if no:
                message {This message should be sent.}
    if no:
        message {This message should not be sent.}""" % (CONDITIONAL_SCHEDULE_START.hour, zero_day(CONDITIONAL_SCHEDULE_START))

survey6 = """header: cohort = __Test__; subtype = one_time; send_hour = %s; date = %s
question 1: auto_append = False; choices = 3; choices_text = %s; resend = %s; """ \
          """parser = multiple_choice_parser {%s}""" % (MULTIPLE_CHOICE_START.hour,
                                                        zero_day(MULTIPLE_CHOICE_START),
                                                        CHOICES_MULTIPLE_CHOICE,
                                                        MULTIPLE_CHOICE_RESEND_TEXT,
                                                        QUESTION_MULTIPLE_CHOICE)

survey7 = """header: cohort = __Test__; subtype = one_time; send_hour = %s; date = %s
attributes: color = blue; shape = circle
question 1: parser = yes_or_no_parser; resend = Please answer yes or no. {%s}
    if yes:
        question 4 {you have [[COLOR]]!}
    if no:
        question 2 {%s}
            if thanks:
                question 5 {you're welcome! have a [[SHAPE]]?}
                    set attribute shape to *answer
if attribute shape is circle:
    question 3 {%s}""" % (SURVEY7_START.hour, zero_day(SURVEY7_START), QUESTION1, QUESTION2, QUESTION3)

survey8 = """header: cohort = __Test__; subtype = one_time; send_hour = %s; date = %s
question 1: auto_append = False; choices = 3; choices_text = %s; resend = %s; parser = multiple_choice_parser {Pick something!}
    if green:
        question 2: auto_append = True; choices = 2; choices_text = %s; resend = %s; parser = multiple_choice_parser {Meh. Second choice?}
            if red:
                message 1 {Merry Christmas!}
    if red:
        message 2 {Ew.}
    if blue:
        message 3 {Good choice.}""" % (SURVEY8_START.hour, zero_day(SURVEY8_START),
                                       SURVEY8_CHOICES, MULTIPLE_CHOICE_RESEND_TEXT,
                                       SURVEY8_SECOND_CHOICES, MULTIPLE_CHOICE_RESEND_TEXT)

survey9 = """header: cohort = __Test__; subtype = one_time; send_hour = %s; date = %s
question 1 {%s}
question 2 {%s}
message {%s}""" % (SURVEY9_START.hour, zero_day(SURVEY9_START),
                   UNICODE_QUESTION1, UNICODE_QUESTION2, UNICODE_MESSAGE)

survey10 = u"""header: cohort = __Test__; subtype = one_time; send_hour = %s; date = %s
attributes: color = %s
question 1: parser = yes_or_no_parser {Answer yes or no.}
    if yes:
        question 2 {Answer this?}
    if no:
        question 3 {Is your favorite color [[COLOR]]?}
    if yes:
        question 4 {Are you an idiot user?}""" %(SURVEY10_START.hour, zero_day(SURVEY10_START), u"marrón")

survey11 = u"""header: cohort = __Test__; subtype = one_time; send_hour = %s; date = %s
question 1 {Answer yes or no.}
    if sí:
        question 2 {Answer this?}
    if non:
        question 3: choices = 2; choices_text = %s; parser = multiple_choice_parser {Choose!}
            if bleu:
                message {"bleu!"}
            if marrón:
                message {"marrón!"}""" %(SURVEY11_START.hour, zero_day(SURVEY11_START), [u"bleu", u"marrón"])

survey12 = """header: cohort = __Test__; subtype = one_time; send_hour = %s; date = %s
question 1: choices = 3; choices_text = %s; parser = multiple_choice_parser {Choose!}
    if blue:
    if green:
        message {Success.}""" %(SURVEY12_START.hour, zero_day(SURVEY12_START), SURVEY8_CHOICES)

survey13 = """header: cohort = __Test2__; subtype = one_time; send_hour = %s; date = %s
question 1: parser = yes_or_no_parser {Answer YES}
    if yes:
        question 2: parser = yes_or_no_parser {Answer NO}
            if no:
                message {This message should be sent.}
    if no:
        message {This message should not be sent.}""" %(SURVEY13_START.hour, zero_day(SURVEY13_START))


class TestIntegration(InstantCensusTestCase):

    def setUp(self):
        self.set_test_items()

    def set_execution_start(self, user, start_time):
        """ ScheduleExecutions are created as part of Schedule.create. These executions need to be cleared
            and remade with param 'start_time' so that executions can correspond to virtual test times """
        for execution in ScheduleExecutions(user_id=user[ID_KEY]):
            execution.remove()
        user.update_schedule_executions(start_time)

    def verify_every_hour(self, new_time, user, predicted_question=None, time_zone=User.DEFAULTS["timezone"]):
        #this function both counts the number of actual sent messages against the number of expected messages
        #and checks that the message content is correct.
        #to do this, the function calls check_messages after running every_hour_core.
        print("You have called sent message count.")
        start_time = convert_to_utc(new_time, time_zone)
        print start_time
        predicted_out_count = len(user.all_messages(incoming=False))
        every_hour_core(user, start_time, delay=False)
        if predicted_question:
            predicted_out_count += 1
        self.check_messages("outgoing", user, predicted_question, predicted_out_count)
        #user.print_executions()

    def verify_on_receive(self, new_time, user, answer, follow_up=None, time_zone=User.DEFAULTS["timezone"]):
        #this function both counts the number of actual received messages against the number of expected messages
        #and checks that the received message content is correct.
        #to do this, the function calls check_messages after running every_hour_core.
        print("You have called received message count.")
        start_time = convert_to_utc(new_time, time_zone)
        predicted_in_count = len(user.all_messages(incoming=True))
        predicted_out_count = len(user.all_messages(incoming=False))
        on_receive(TEST_COHORT_PHONENUM, user["phonenum"], answer, start_time, delay=False)
        predicted_in_count += 1 #retain as a separate line for print-statements
        self.check_messages("incoming", user, answer, predicted_in_count)
        if follow_up:
            predicted_out_count += 1
            self.check_messages("outgoing", user, follow_up, predicted_out_count)
        else:
            self.check_messages("outgoing", user, None, predicted_out_count)

    def compile_survey_and_verify_manual_run(self, user, survey, predicted_question):
        globals()['ENABLE_FAST_FORWARD'] = True
        current_time = now()
        test_cohort = Cohort.get_test_cohort()
        compile_survey(survey)
        survey_object = Schedules()[-1]
        print survey_object
        predicted_out_count = len(user.all_messages(incoming=False))
        print predicted_out_count
        manually_run_schedule_core(survey_object, test_cohort, current_time)
        print len(user.all_messages(incoming=False))
        predicted_out_count += 1 #retain as a separate line for print-statements
        self.check_messages("outgoing", user, predicted_question, predicted_out_count)

    def check_messages(self, direction, user, predicted_text, prediction_count):
        #checks the number of actual messages received or sent against the expected number of messages
        #retrieves the text of the most recent received or sent message
        #and verifies that it is the expected message.
        print("You have called check messages")
        if predicted_text != None and direction == "outgoing":
            predicted_text = check_for_problem_characters(predicted_text)
        if prediction_count == 0 or predicted_text == None:
            actual_count = len(user.all_messages(incoming=False))
            self.assertEqual(actual_count, prediction_count, "An unexpected outgoing message was sent!")
            return
        if direction == "outgoing":
            print user.all_messages(incoming=False)[-1]["text"]
            print len(user.all_messages(incoming=False))
            user.print_executions()
            actual_count = len(user.all_messages(incoming=False))
            text = user.all_messages(incoming=False)[-1]["text"]
            self.assertEqual(actual_count, prediction_count, "Incorrect number of outgoing messages!")
        else:
            print user.all_messages(incoming=True)[-1]["text"]
            print len(user.all_messages(incoming=True))
            actual_count = len(user.all_messages(incoming=True))
            text = user.all_messages(incoming=True)[-1]["text"]
            self.assertEqual(actual_count, prediction_count, "Incorrect number of incoming messages!")
        #print predicted_text
        self.assertEqual(text, predicted_text, "Your %s message has the wrong text." % direction)

    ################################################################################
    ##############################         TESTS         ###########################
    ################################################################################

    def test_recurring(self):
        compile_survey(survey1)
        user = User.get_test_user()
        #set a start time
        start_time = now().replace(hour=12) + timedelta(days=1)
        #set up
        self.set_execution_start(user, start_time + timedelta(days=-1))
        self.verify_every_hour(now().replace(hour=11) + timedelta(days=-5), user)
        #check sent messages
        self.verify_every_hour(start_time, user, QUESTION1)
        #set new time
        next_time = now().replace(hour=12).replace(minute=10) + timedelta(days=1)
        #check receive messages
        self.verify_on_receive(next_time, user, "yes", QUESTION2)

    def test_set_conditional_attribute(self):
        compile_survey(survey7)
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY7_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent message
        self.verify_every_hour(start_time, user, QUESTION1)
        #check that if answer is no, QUESTION2 is sent
        self.verify_on_receive(start_time, user, "no", QUESTION2)
        #check that if answer is NOT thanks, QUESTION3 is sent
        self.verify_on_receive(start_time, user, "blah", QUESTION3)

    def test_attribute_insertion(self):
        compile_survey(survey7)
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY7_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent message
        self.verify_every_hour(start_time, user, QUESTION1)
        #check that if answer is yes, follow-up message is "you have blue!"
        self.verify_on_receive(start_time, user, "yes", "you have blue!")
        #check final question is sent
        self.verify_on_receive(start_time, user, "anything", QUESTION3)
        #check no other things sent
        self.verify_every_hour(start_time + timedelta(hours=2), user)

    def test_answer_to_attribute(self): #TODO FIX
        compile_survey(survey7)
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY7_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent message
        self.verify_every_hour(start_time, user, QUESTION1)
        #check that if answer is no, QUESTION2 is sent
        self.verify_on_receive(start_time, user, "no", QUESTION2)
        #check that if answer is yes, a question with [[SHAPE]] is sent
        self.verify_on_receive(start_time, user, "thanks", "you're welcome! have a circle?")
        #attribute SHAPE is reset to answer "square"
        self.verify_on_receive(start_time, user, "square")

    def test_resend_attribute(self):
        compile_survey(survey7)
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY7_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent message
        self.verify_every_hour(start_time, user, QUESTION1)
        #check that if answer is no, QUESTION2 is sent
        self.verify_on_receive(start_time, user, "no", QUESTION2)
        #check that if answer is yes, a question with [[SHAPE]] is sent
        self.verify_on_receive(start_time, user, "thanks", "you're welcome! have a circle?")
        #no response! check if a resend is sent by the next day
        new_time = start_time + timedelta(days=1)
        self.verify_every_hour(new_time, user, "you're welcome! have a circle?")
        #no response again! check another day:
        new_time = new_time + timedelta(days=1)
        self.verify_every_hour(new_time, user, "you're welcome! have a circle?")

    def test_resend_yes_or_no(self):
        compile_survey(survey7)
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY7_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent message
        self.verify_every_hour(start_time, user, QUESTION1)
        #check that if answer is neither yes or no, a "please answer yes or no" resend follows
        self.verify_on_receive(start_time, user, "fork", "Please answer yes or no. %s" % QUESTION1)
        #check that if answer is still neither yes or no, a "Please answer yes or no" resend follows.
        self.verify_on_receive(start_time, user, u"spørk", "Please answer yes or no. %s" % QUESTION1)
        #one more bad answer, which should continue the survey
        self.verify_on_receive(start_time, user, "snork", QUESTION3)
        #check no other things sent
        self.verify_every_hour(start_time + timedelta(hours=2), user)

    def test_multiple_choice_conditional(self):
        compile_survey(survey8)
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY8_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent question
        self.verify_every_hour(start_time, user, "Pick something!")
        #check that if the answer is blue, the message received is "Good choice."
        self.verify_on_receive(start_time, user, "blue", "Good choice.")
        #check nothing else sent
        self.verify_every_hour(start_time + timedelta(hours=2), user)

    def test_nested_multiple_choice(self):
        compile_survey(survey8)
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY8_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent question
        self.verify_every_hour(start_time, user, "Pick something!")
        #check that if the answer is green, a new multiple choice question is sent with an appended text
        appended_text = "Meh. Second choice? red, or green?"
        self.verify_on_receive(start_time, user, "green", appended_text)
        #check that if the answer is red, message 1 and not message 2 is sent
        self.verify_on_receive(start_time, user, "red", "Merry Christmas!")
        #check nothing else sent
        self.verify_every_hour(start_time + timedelta(hours=2), user)

    def test_multiple_choice_skip(self):
        compile_survey(survey8)
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY8_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent question
        self.verify_every_hour(start_time, user, "Pick something!")
        #check that if the answer is red, message 2 but not message 1 is sent
        self.verify_on_receive(start_time, user, "red", "Ew.")
        #check nothing else is sent
        self.verify_every_hour(start_time + timedelta(hours=2), user)

    def test_unicode_sends(self):
        #test unicode questions being sent out
        compile_survey(survey9)
        user = User.get_test_user()
        #set start time
        start_time = SURVEY9_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent question
        self.verify_every_hour(start_time, user, UNICODE_QUESTION1)
        #check a response triggers question 2
        self.verify_on_receive(start_time, user, "Not really.", UNICODE_QUESTION2)
        #check a response -> final message
        self.verify_on_receive(start_time, user, "Thaaaanks.", UNICODE_MESSAGE)

    def test_unicode_received(self):
        #tests open-parser answers written in unicode
        compile_survey(survey9)
        user = User.get_test_user()
        #set start time
        start_time = SURVEY9_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent question
        self.verify_every_hour(start_time, user, UNICODE_QUESTION1)
        #check a response triggers question 2
        self.verify_on_receive(start_time, user, u"Sí non.", UNICODE_QUESTION2)
        #check a response -> final message
        self.verify_on_receive(start_time, user, u"Thaaaa√∫˜µ¬πks.", UNICODE_MESSAGE)

    def test_one_time_survey(self):
        compile_survey(survey2)
        user = User.get_test_user()
        #set a start time
        start_time = ONE_TIME_START
        #rewind an hour and check nothing sent early
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check sent messages
        self.verify_every_hour(start_time, user, QUESTION3)

    def test_timezones(self):
        compile_survey(survey3)
        #set two users
        cohort = Cohort.get_test_cohort()
        user1 = User.create("+18885555555", cohort[ID_KEY])
        user2 = User.create("+18885555556", cohort[ID_KEY])
        #set user timezones
        user1.update({"timezone": "US/Central"})
        user2.update({"timezone": "US/Pacific"})
        #set start_time without a timezone
        start_time = TIMEZONE_SCHEDULE_START
        #set up for US/Central start_time
        self.set_execution_start(user1, convert_to_utc(start_time, "US/Central"))
        self.verify_every_hour(start_time + timedelta(hours=-1), user1, None, "US/Central")
        self.set_execution_start(user2, convert_to_utc(start_time, "US/Central"))
        self.verify_every_hour(start_time + timedelta(hours=-1), user2, None, "US/Central")
        #start test at US/Central start_time
        self.verify_every_hour(start_time, user1, QUESTION3, "US/Central")
        self.verify_every_hour(start_time, user2, None, "US/Central")
        #start test at Pacific time
        self.verify_every_hour(start_time, user2, QUESTION3, "US/Pacific")
        self.verify_every_hour(start_time, user1, None, "US/Pacific")

    def test_onboard(self):
        compile_survey(survey4)
        user = User.get_test_user()
        #onboard the user, as this test is checking whether the standard first message
        # is sent upon adding a user (no users overboard!)
        onboard_user(user, now().replace(hour=11) + timedelta(days=1), delay=False)
        #check whether the first message is actually sent
        self.check_messages("outgoing", user, QUESTION4, 2)

    def test_conditional_execution_bug(self):
        compile_survey(survey5)
        user = User.get_test_user()
        #set a start time
        start_time = CONDITIONAL_SCHEDULE_START
        #set up and check nothing sent early
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check first sent message, "Answer YES"
        self.verify_every_hour(start_time, user, "Answer YES")
        #answer "yes", which triggers the follow-up sent message "Answer NO"
        self.verify_on_receive(start_time, user, "yes", "Answer NO")
        #answer "no," which should trigger the follow-up sent message "This message should be sent"
        self.verify_on_receive(start_time, user, "no", "This message should be sent.")

    def test_multiple_choice(self):
        compile_survey(survey6)
        user = User.get_test_user()
        #set start time
        start_time = MULTIPLE_CHOICE_START
        #set up and check the previous hour
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check first sent message, QUESTION_MULTIPLE_CHOICE
        self.verify_every_hour(start_time, user, QUESTION_MULTIPLE_CHOICE)
        #respond with gobbledygook, which triggers the follow-up response defined below
        follow_up = "%s %s" % (MULTIPLE_CHOICE_RESEND_TEXT, QUESTION_MULTIPLE_CHOICE)
        self.verify_on_receive(start_time, user, "gobbledygook", follow_up)
        #respond with correct answer! yay!
        self.verify_on_receive(start_time, user, CHOICES_MULTIPLE_CHOICE[0])

    def test_resends(self):
        compile_survey(survey1)
        user = User.get_test_user()
        #set initial start time
        start_time = now().replace(hour=12) + timedelta(days=1)
        #set up and clear executions
        self.set_execution_start(user, now().replace(hour=11) + timedelta(days=-7))
        self.verify_every_hour(now().replace(hour=11) + timedelta(days=-7), user)
        #check first sent message
        self.verify_every_hour(start_time, user, QUESTION1)
        #update time
        update_time = now().replace(hour=15) + timedelta(days=1)
        #check for first resend
        self.verify_every_hour(update_time, user, QUESTION1)
        #update time again, and check for no other resend
        update_time = now().replace(hour=17) + timedelta(days=1)
        self.verify_every_hour(update_time, user)
        #another time update (it's a new dawn, it's a new day!) and resend
        update_time = now().replace(hour=15) + timedelta(days=2)
        self.verify_every_hour(update_time, user, QUESTION1)
        #another hour, and now finally the user gets around to replying to question 1
        update_time = now().replace(hour=16) + timedelta(days=2)
        self.verify_on_receive(update_time, user, "yes", QUESTION2)
        #now the user replies to question 2
        self.verify_on_receive(update_time, user, "yes")
        #and, finally, we check that no more resends are going out, evah
        update_time = now().replace(hour=15) + timedelta(days=3)
        self.verify_every_hour(update_time, user)


    def test_unicode_yes_no_parser(self):
        compile_survey(survey5)
        user = User.get_test_user()
        #set start time
        start_time = CONDITIONAL_SCHEDULE_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check first sent question, "Answer YES"
        self.verify_every_hour(start_time, user, "Answer YES")
        #answer "yes", which triggers the follow-up sent message "Answer NO"
        self.verify_on_receive(start_time, user, u"yeah ☺", "Answer NO")
        #answer "no," which should trigger the follow-up sent message "This message should be sent"
        self.verify_on_receive(start_time, user, u"nô", "This message should be sent.")

    def test_unicode_multiple_choice(self):
        compile_survey(survey8)
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY8_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent question
        self.verify_every_hour(start_time, user, "Pick something!")
        #check that if the answer is blue, the message received is "Good choice."
        self.verify_on_receive(start_time, user, u"blue ☺", "Good choice.")
        #check nothing else sent
        self.verify_every_hour(start_time + timedelta(hours=2), user)

    def test_unicode_multiple_choice_2(self):
        compile_survey(survey8)
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY8_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent question
        self.verify_every_hour(start_time, user, "Pick something!")
        #an invalid answer gets a resend
        follow_up = "%s %s" % (MULTIPLE_CHOICE_RESEND_TEXT, "Pick something!")
        self.verify_on_receive(start_time, user, u"blee ☺", follow_up)
        #send a valid answer
        self.verify_on_receive(start_time, user, u"blue", "Good choice.")
        #check nothing else sent
        self.verify_every_hour(start_time + timedelta(hours=2), user)

    def test_incomplete_multiple_choice(self):
        compile_survey(survey12)
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY12_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent question
        self.verify_every_hour(start_time, user, "Choose!")
        #check that choosing "blue" yields no response
        self.verify_on_receive(start_time, user, "blue")
        #check nothing else sent
        self.verify_every_hour(start_time + timedelta(hours=2), user)

    def test_incomplete_multiple_choice_2(self):
        compile_survey(survey12)
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY12_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent question
        self.verify_every_hour(start_time, user, "Choose!")
        #check that choosing "red" yields no response
        self.verify_on_receive(start_time, user, "red")
        #check nothing else sent
        self.verify_every_hour(start_time + timedelta(hours=2), user)

    def test_incomplete_multiple_choice_3(self):
        compile_survey(survey12)
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY12_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first sent question
        self.verify_every_hour(start_time, user, "Choose!")
        #check that choosing "blue" yields a response (finally!)
        self.verify_on_receive(start_time, user, "green", "Success.")
        #check nothing else sent
        self.verify_every_hour(start_time + timedelta(hours=2), user)

    def test_unicode_attribute(self):
        #test unicode attribute
        compile_survey(survey10)
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY10_START
        #run a pre-check and clear executions
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check for first question sent
        self.verify_every_hour(start_time, user, "Answer yes or no.")
        #check for answer no, and subsequent question with a unicode attribute
        self.verify_on_receive(start_time, user, "no", u"Is your favorite color marrón?")

    def test_copied_schedule(self):
        #integration test for a schedule copied into the __Test__ cohort from another cohort
        #first, create a new cohort, which requires logging in to the dashboard
        test_app = app.test_client()
        resp = test_admin_log_in_response(test_app)
        self.assertRedirect(resp, "Bad login.")
        # create_cohort()
        new_cohort_name = "__Test2__"
        resp = create_new_cohort_response(test_app, new_cohort_name)
        self.assertResponseOkay(resp, "Bad return status on /create_cohort")
        #copy survey from new cohort to __Test__ cohort
        resp = copy_survey_to_cohort_response(test_app, "__Test__", survey13)
        self.assertResponseOkay(resp, "Bad return status on /copy_survey")
        #get the test user
        user = User.get_test_user()
        #set a start time
        start_time = SURVEY13_START
        #precheck, etc.
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check first sent message, "Answer YES"
        self.verify_every_hour(start_time, user, "Answer YES")
        #answer "yes", which triggers the follow-up sent message "Answer NO"
        self.verify_on_receive(start_time, user, "yes", "Answer NO")
        #answer "no," which should trigger the follow-up sent message "This message should be sent"
        self.verify_on_receive(start_time, user, "no", "This message should be sent.")

    def test_two_overlapping_schedules(self):
        compile_survey(survey8)
        compile_survey(survey12)
        user = User.get_test_user()
        #set start time to the start time for survey 12
        start_time = SURVEY12_START
        #precheck, yadda yadda
        self.set_execution_start(user, start_time)
        self.verify_every_hour(start_time + timedelta(hours=-1), user)
        #check first sent message from survey 12
        self.verify_every_hour(start_time, user, "Choose!")
        #buuuuut no response from the user, and suddenly it's start time for survey 8!
        new_time = SURVEY8_START
        #check first question from survey 8
        self.verify_every_hour(new_time, user, "Pick something!")
        #respond to survey 8 question, and receive two answers in response
        #self.verify_on_receive(new_time, user, "blue", "Good choice.")
        on_receive(TEST_COHORT_PHONENUM, user["phonenum"], "blue", start_time, delay=False)
        self.check_messages("outgoing", user, "Choose!", 4) #4 total outgoing messages
        #respond to Choose!
        self.verify_on_receive(new_time, user, "blue")










        #################### TESTS THAT FAIL ###############################################
    #
    # def test_double_yes(self):
    #     #test idiot user who has two if-yes statements
    #     compile_survey(survey10)
    #     user = User.get_test_user()
    #     #set a start time
    #     start_time = SURVEY10_START
    #     #run a pre-check and clear executions
    #     self.set_execution_start(user, start_time)
    #     self.verify_every_hour(start_time + timedelta(hours=-1), user)
    #     #check for first question sent
    #     self.verify_every_hour(start_time, user, "Answer yes or no.")
    #     #check for answer no, and subsequent question with a unicode attribute
    #     self.verify_on_receive(start_time, user, "yes", "Answer this?")
    #     #check to see if second question sent
    #     self.verify_on_receive(start_time, user, "blahblahblah", "Are you an idiot user?")
    #     #crash system! second if-yes question not sent out!
    #
    # def test_unicode_in_conditional(self):
    #     #test unicode in if-X conditional statement
    #     compile_survey(survey11)
    #     user = User.get_test_user()
    #     #set a start time
    #     start_time = SURVEY11_START
    #     #run a pre-check and clear executions
    #     self.set_execution_start(user, start_time)
    #     self.verify_every_hour(start_time + timedelta(hours=-1), user)
    #     #check for first question sent
    #     self.verify_every_hour(start_time, user, "Answer yes or no.")
    #     #check for answer sí, which has unicode in it
    #     self.verify_on_receive(start_time, user, u"sí", "Answer this?")
    #     #check for no more questions
    #     self.verify_every_hour(start_time + timedelta(hours=2), user)
    #     #system crashes because conditional has unicode in it
    #
    # def test_unicode_multiple_choice_answer(self):
    #     #test unicode in multiple choice answers
    #     compile_survey(survey11)
    #     user = User.get_test_user()
    #     #set a start time
    #     start_time = SURVEY11_START
    #     #run a pre-check and clear executions
    #     self.set_execution_start(user, start_time)
    #     self.verify_every_hour(start_time, user, "Answer yes or no.")
    #     #check for answer non, to get to unicode multiple choice question
    #     self.verify_on_receive(start_time, user, u"non", "Choose!")
    #     #answer bleu, in unicode, no accents
    #     self.verify_on_receive(start_time, user, u"bleu", u"bleu!")
    #     #check for no more questions
    #     self.verify_every_hour(start_time + timedelta(hours=2), user)
    #     #system crashes! doesn't matter the lack of accents
    #
    # def test_manually_run_schedule(self):
    #     #set up user and clear executions
    #     user = User.get_test_user()
    #     self.set_execution_start(user, now())
    #     self.verify_every_hour(now() + timedelta(hours=-1), user)
    #     #compile a survey with one question and manually run
    #     self.compile_survey_and_verify_manual_run(user, survey3, QUESTION3)
















    # previous test hanging around, edited to be run under new suite

    #
    #
    # def test_manually_run_schedule_previous(self):
    #     globals()['ENABLE_FAST_FORWARD'] = True
    #     user = User.get_test_user()
    #     curr_time = now()
    #     test_cohort = Cohort.get_test_cohort()
    #     test_cohort_id = test_cohort[ID_KEY]
    #     compile_survey(survey3)
    #     schedule7 = Schedules()[-1]
    #     question = Question.create(
    #         {"cohort_id": test_cohort_id, "text": QUESTION_FOR_S7}, random_id=True
    #     )
    #     schedule7.add_action("send_question", {"database_id": question[ID_KEY]})
    #     count = len(user.messages(incoming=False))
    #     manually_run_schedule_core(schedule7, test_cohort, curr_time)
    #     self.assertEqual(len(user.messages(incoming=False)), count + 1,
    #                      "Schedule didn't send question")
    #     text = user.messages(incoming=False)[-1]["text"]
    #     self.assertEqual(text, QUESTION_FOR_S7, "Sent message has wrong text: %s" % text)



