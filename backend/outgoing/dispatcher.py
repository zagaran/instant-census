from backend.outgoing.exit_points import send_control_message
from conf.settings import DISABLE_WELCOME, DISABLE_INACTIVE_STATUS, \
    DISABLE_USER_STATUS_CHANGE_MESSAGES, DISABLE_COHORT_STATUS_CHANGE_MESSAGES
from constants import messages


def send_welcome(user):
    welcome_message = user.get_cohort()["welcome_message"]
    # if welcome_message is None, no message is sent
    if DISABLE_WELCOME or welcome_message is None:
        return
    welcome_message = welcome_message + messages.LEGALLY_REQUIRED
    send_control_message(user, welcome_message, delay=False)

def send_password(user):
    user.new_password()
    send_control_message(user, messages.PASSWORD, delay=False)

def send_waitlist(user):
    #for msg in user.get_cohort()["waitlist_messages"]: send_control_message(user, msg)
    send_control_message(user, user.get_cohort()["waitlist_message"], delay=False)

def send_pending(user):
    #for msg in user.get_cohort()["pending_messages"]: send_control_message(user, msg)
    send_control_message(user, user.get_cohort()["pending_message"], delay=False)

def send_stop_word_in_message(user, word):
    send_control_message(user, messages.STOP_WORD_IN_MESSAGE % word, delay=False)

def send_bad_access_code(user):
    send_control_message(user, messages.BAD_ACCESS_CODE, delay=False)

def send_crisis_message(user):
    send_control_message(user, messages.CRISIS, delay=False)

def send_promote_from_waitlist(user):
    send_control_message(user, messages.WAITLIST_PROMOTION, delay=False)

def send_inactive_message(user):
    if not DISABLE_INACTIVE_STATUS and not DISABLE_USER_STATUS_CHANGE_MESSAGES:
        send_control_message(user, messages.INACTIVE, delay=False)

def send_user_reactivation_message(user):
    if not DISABLE_USER_STATUS_CHANGE_MESSAGES:
        message = messages.DEFAULT_USER_RESTART
        send_control_message(user, message, delay=False)
    
def send_user_pause_message(user):
    if not DISABLE_USER_STATUS_CHANGE_MESSAGES:
        send_control_message(user, messages.DEFAULT_USER_PAUSE, delay=False)
    
def send_cohort_reactivation_message(user):
    if not DISABLE_COHORT_STATUS_CHANGE_MESSAGES:
        message = messages.DEFAULT_COHORT_RESTART
        send_control_message(user, message, delay=False)

def send_cohort_pause_message(user):
    if not DISABLE_COHORT_STATUS_CHANGE_MESSAGES:
        send_control_message(user, messages.DEFAULT_COHORT_PAUSE, delay=False)
    
def send_paused_cohort_user_restart_message(user):
    if not DISABLE_COHORT_STATUS_CHANGE_MESSAGES:
        send_control_message(user, messages.DEFAULT_PAUSED_COHORT_USER_RESTART, delay=False)
