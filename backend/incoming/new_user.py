from time import sleep
from threading import Thread
from mongolia.errors import DatabaseConflictError

from conf.settings import BYPASS_START_WORDS
from constants.exceptions import BadPhoneNumberError
from backend.outgoing.dispatcher import (send_welcome, send_waitlist,
    send_bad_access_code, send_pending)
from constants.parser_consts import START_WORDS
from database.backbone.cohorts import Cohort, ID_KEY
from database.tracking.access_codes import AccessCode
from database.tracking.users import User, Status
from utils.formatters import parser_format, phone_humanize
from utils.codes import looks_like_an_access_code
from backend.features.schedule_features import run_on_user_creation_schedules
from backend.admin_portal.common_helpers import raise_400_error, validate_cohort
from utils.logging import log_warning
from utils.time import now
from constants.cohorts import CohortStatus


def new_user_via_sms(phonenum, ic_number, message_text, curr_time, delay=True):
    cohort = Cohort(ic_numbers=ic_number)
    # Access codes not deployed
    #if cohort["access_code_required"] or looks_like_an_access_code(message_text):
    #    user = handle_access_code(phonenum, ic_number, cohort, message_text)
    if cohort["enableable_from_sms"] and (parser_format(message_text) in START_WORDS or BYPASS_START_WORDS):
        user = User.create(phonenum, cohort[ID_KEY], status=Status.active)
    else:
        user = User.create(phonenum, cohort[ID_KEY], status=Status.pending)
        user["needs_review"] = True
    #TODO: refactor following two lines
    user["custom_attributes"] = cohort["custom_attributes"]
    user.save()
    #if cohort["status"] == CohortStatus.active:
    if user["status"] == Status.active:
        onboard_user(user, curr_time, delay)
    elif user["status"] == Status.pending and cohort["enableable_from_sms"]: send_pending(user)
    # Should not hit these two lines yet, since we don't have waitlist/invalid currently implemented
    elif user["status"] == Status.waitlist: send_waitlist(user)
    elif user["status"] == Status.invalid: send_bad_access_code(user)
    return user

def handle_access_code(phonenum, ic_number, cohort, message_text):
    access_code = parser_format(message_text).upper()
    access_code = AccessCode.retrieve(access_code)
    if access_code is None or not access_code.valid(ic_number):
        user = User.create(phonenum, cohort[ID_KEY], status=Status.invalid)
        return user
    access_code_cohort = access_code.get_cohort()
    if access_code_cohort is not None: cohort = access_code_cohort
    user = User.create(phonenum, cohort[ID_KEY], status=Status.active)
    user["access_code"] = access_code[ID_KEY]
    access_code["user"] = user["phonenum"]
    user.save()
    access_code.save()
    return user

def handle_access_code_resubmit(user, message_text):
    curr_time = now()
    access_code = parser_format(message_text).upper()
    access_code = AccessCode.retrieve(access_code)
    if access_code is None or not access_code.valid(user["ic_number"]):
        return False
    user.update(cohort_id=access_code["cohort_id"], access_code=access_code[ID_KEY])
    user.set_status(Status.active)
    access_code["user"] = user["phonenum"]
    access_code.save()
    onboard_user(user, curr_time)
    return user

def new_user_via_admin_portal(phonenum, cohort_id, curr_time, delay=True):
    try:
        user = User.retrieve(phonenum=phonenum, cohort_id=cohort_id)
    # if phone number is invalid
    except BadPhoneNumberError:
        raise_400_error("Invalid phone number.")
    except DatabaseConflictError:
        # alert engineering to this potential problem
        log_warning(("Multiple users were returned for User.retrieve() via new_user_via_admin_portal():\n\n" +
                     "Phone Number: %s\nCohort ID: %s\n Current Time: %s" % (phonenum, cohort_id, curr_time)))
        # alert admin user to not being able to create new user
        raise_400_error("A user with phone number '%s' already exists." % phone_humanize(phonenum))
    # if user already exists, raise error
    if user:
        raise_400_error("A user with phone number '%s' already exists." % phone_humanize(phonenum))
    else:
        cohort = validate_cohort(cohort_id)
        user = User.create(phonenum, cohort[ID_KEY], status=Status.active)
        onboard_user(user, curr_time, delay)
    return user

def onboard_user(user, curr_time, delay=True):
    if user.is_active() and user.cohort_is_active():  # cohort status is checked every time, so TODO: optimize
        thread = Thread(target=_onboard_user_core, args=(user, curr_time, delay))
        thread.start()
        if not delay:
            thread.join()

def _onboard_user_core(user, curr_time, delay):
    send_welcome(user)
    user.update(onboarded=True)
    run_on_user_creation_schedules(user, curr_time, delay=delay)
