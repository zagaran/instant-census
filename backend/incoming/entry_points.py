###########################################################
import utils.database # @UnusedImport to establish mongo conn
import backend.actions  # @UnusedImport to fill out ACTIONS
###########################################################

from multiprocessing.pool import ThreadPool
from random import randint
from threading import Thread
from time import sleep
from timeit import default_timer

from mongolia.constants import ID_KEY

from backend.features.response_handlers import (crisis_message_handler,
    control_message_handler)
from backend.features.schedule_features import run_schedules
from backend.incoming.new_user import new_user_via_sms, handle_access_code_resubmit
from backend.incoming.processing import (handle_message, inactive_user,
    reactivate_user)
from conf.settings import NEEDS_REVIEW_INBOX, EVERY_HOUR_RANDOM_DELAY, EVERY_HOUR_THREADCOUNT
from constants.exceptions import BadPhoneNumberError
from database.analytics.system_load import CronTime
from database.backbone.cohorts import Cohort
from database.tracking.messages import ControlMessage, Message
from database.tracking.users import User, Users, Status
from utils.concurency import UserLock
from utils.formatters import phone_format, parser_format
from utils.logging import log_error, log_thread, log_warning
from utils.time import now


def on_receive(ic_number, phonenum, message_body, receive_time, twilio_message_sid=None, delay=True):
    try:
        phonenum = phone_format(phonenum)
        ic_number = phone_format(ic_number)
    except BadPhoneNumberError as e:
        log_error(e, "Error in formatting phone number in backend.texting.on_receive")
    thread = Thread(target=on_receive_core,
                    args=(ic_number, phonenum, message_body, receive_time, twilio_message_sid, delay))
    thread.start()
    if not delay:
        thread.join()


@log_thread
def on_receive_core(ic_number, phonenum, raw_message_body, receive_time, twilio_message_sid, delay=True):
    """ Once you are done mucking around in this function, increment the following counter:
            total_hours_wasted_here = 78 """
    with UserLock(phonenum) as this_thread:
        formatted_message = parser_format(raw_message_body)
        user = User.retrieve(phonenum=phonenum, ic_number=ic_number)
        needs_review = False
        # if user is texting in from a different ic_number on his/her Cohort
        if user is None:
            # even though ic_numbers is list, Mongo returns a Cohort if ic_number exists in that list
            cohort = Cohort(ic_numbers=ic_number)
            user = User.retrieve(phonenum=phonenum, cohort_id=cohort[ID_KEY])
        # if new user
        if user is None:
            user = new_user_via_sms(phonenum, ic_number, raw_message_body,
                                    receive_time, delay=delay)
            cohort = Cohort(user["cohort_id"])
            if not cohort["enableable_from_sms"]:
                needs_review = True
        elif user["status"] == Status.invalid:
            ControlMessage.store(phonenum, raw_message_body, True, ic_number, receive_time, twilio_message_sid)
            handle_access_code_resubmit(user, raw_message_body)
            return
        if NEEDS_REVIEW_INBOX:
            user.update({"needs_review": True})
            needs_review = True
        if control_message_handler(user, formatted_message):
            ControlMessage.store(user, raw_message_body, True, receive_time, twilio_message_sid)
            return
        if reactivate_user(user):
            pass  # Continue execution
        if crisis_message_handler(user, formatted_message):
            needs_review = True
            pass  # Continue execution
        
        #see commit 58dc88f; code commented out due to incorrect handling of double incoming messages
#       if this_thread.is_responder():
        message = Message.store_incoming(user, raw_message_body, receive_time, needs_review, twilio_message_sid)
        handle_message(user, receive_time, message, formatted_message, raw_message_body, delay)
#       else:
#           # TODO: handle correction messages here (messages starting with "*")
#           message = user.last_received()
#           message.append(raw_message_body)


@log_thread
def every_hour():
    """ WARNING: DO NOT CALL THIS FUNCTION DIRECTLY FROM CRON.
        This function runs every hour to check active users for resends and
        schedules that have become active.  This function should only be called
        via the dispatch_every_hour page so that it shares concurrency control
        with on_receive. """
    if EVERY_HOUR_RANDOM_DELAY:
        minutes_of_delay = randint(1, 20)
        sleep(minutes_of_delay * 60)
    start_time = now()
    start = default_timer()
    job_start = now()
    
    # instantiate a threadpool with thread count equal to the value in settings.
    pool = ThreadPool(EVERY_HOUR_THREADCOUNT)
    
    # obnoxious problem: we need to stick the close and terminates in a finally clause
    try:
        # args below is a generator of tuples from an iterator database query, should be 100% lazy.
        args = ((user, job_start) for user in Users.active())
    
        # imap_unordered returns an iterator over the return values of every operation. We don't
        # actually care about return values here (every_hour_core is self-contained), but we do
        # want the number of users we iterated over.
        
        # imap_unordered is the most efficient thread dispatch pattern of threadpools.
        # imap means it does not internally convert the args to a list.
        
        # unordered means it does not retain order in the list that it returns (element i in the
        # list of returns values does not necessarily correspond to element i of the passed in
        # arguments. We don't care about order, so this is fine.)
        ret_iterator = pool.imap_unordered(every_hour_core_threadpool_function, args)
    
        # imap_unordered proceeds automatically, but we have to safely block until operations
        # finish. Annoyingly, if any of the threads raised an exception that will be re-raised
        # upon iteration. every_hour_core is wrapped with the log_thread decorator, so these
        # exceptions will have sentry error reports and/or print the the stack traces.
        i = 0
        while True:
            try:
                i += 1
                print "done with every_hour_core process", i
                ret_iterator.next()
            except StopIteration:
                break  # Done, exit loop.
            except Exception:
                pass  # log_error decorator means we can just pass here.
    except Exception:
        # This is purely present to allow the use of the finally statement, use bare raise
        # statement to preserve stack traces.
        raise
    finally:
        pool.close()
        pool.terminate()
    
    end = default_timer()
    CronTime.store("every_hour", end - start, start_time, ret_iterator._length)
    if end - start > 2400:
        # Warn if every_hour took more than 40 minutes to run
        log_warning("Every hour took %s minutes to run" % ((end - start) / 60))

def every_hour_core_threadpool_function(args):
    # exists purely to unpack variables
    user, job_start = args
    return every_hour_core(user, job_start)
    

@log_thread
def every_hour_core(user, job_start, delay=True):
    with UserLock(user["phonenum"]):
        if inactive_user(user):
            return
        if run_schedules(user, job_start, delay=delay):
            return
