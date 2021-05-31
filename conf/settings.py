#############################################
########### PREMIUM FEATURES !!! ############
#############################################

# If set to True, welcome message is disabled
DISABLE_WELCOME = False

# If set to True, frontend and backend check for 160 characters will be extended to 1600 characters
DISABLE_LENGTH_RESTRICTION = False

# If set, default welcome message contents overridden to what is set. Must be string.
# Note: If customer want to white-label their welcome message, charge for it.
CUSTOM_WELCOME_OVERRIDE = None

# If set to True, users with status deleted still shows up in user management portal
# WARNING: If this is set to True and there are phone numbers on a cohort that have been deleted and then re-added, this
#          will show multiple users with the same phone numbers on that same cohort, which may confuse admins who aren't
#          aware, since most people expect that deleted users are deleted
SHOW_DELETED_USERS = False

# If set to True, admins will not be able to reset their password
DISABLE_PASSWORD_RESET = False

# If set to True, admins will be able to fast forward schedules
ENABLE_FAST_FORWARD = False

# If set to False, admins will not be able to test schedules with a subset of Users
ENABLE_SCHEDULE_TESTING = True

# If set to True, needs review becomes an inbox that marks all incoming messages as needing review
NEEDS_REVIEW_INBOX = False

# If set to True, calculates needs review counts
NEEDS_REVIEW_COUNTS = True

# If set to True, displayed cohorts are on the admin level instead of customer level
# However, this does not protect the API from admins modifying other admins' cohorts
ADMIN_LEVEL_VISIBILITY = False

# If set to True, exposes frontend to allow admins to change timezones, which
# will modify schedule executions by time zone
TIMEZONE_SUPPORT = False

# If set to True, disables cohort status change messages
DISABLE_COHORT_STATUS_CHANGE_MESSAGES = False

# If set to True, disables user status change messages
DISABLE_USER_STATUS_CHANGE_MESSAGES = False

# If set to True, adds a 1 to 20 minute delay before starting every hour
EVERY_HOUR_RANDOM_DELAY = False

# If set to True, allows sending to phone numbers outside the US
ALLOW_INTERNATIONAL_SENDING = False

# If set to True, anyone who would be set to Inactive is in instead set to Completed
DISABLE_INACTIVE_STATUS = False

# Number of Bad Response Resends allowed before survey skips the question and moves on
BAD_RESPONSE_RESEND_LIMIT = 2

# If set to False, does not append question text to bad response resend
BAD_RESPONSE_RESEND_QUESTION_APPEND = True

#############################################
########### TESTING FEATURES !!! ############
#############################################
# If set to True, will show data reports as available tab for users
DATA_REPORTS_FEATURE = True

# If set to a number, that number will be the limit on messages sent each month. If None, there will be no limit
MONTHLY_MSG_USAGE_LIMIT = None

# If set to a number, that number will be the lifetime limit on messages sent total on that system/server.
LIFETIME_MSG_USAGE_LIMIT = None

# If set to a number, that number will be the limit on number of cohorts deployed.
COHORTS_LIMIT = None

# If set to a number, that number will be the limit on number of users allowed WITH A IC NUMBER in a cohort.
COHORT_USER_LIMIT = None

# If set, adds these words to START_WORDS (expects a list of strings)
CUSTOM_START_WORDS = []

# If set to True, stop resends of interrupted schedules. E.g. Stops system behavior of: if Schedule A is interrupted 
# with Schedule B and B is finished, interrupted schedule A gets resent.
STOP_INTERRUPTED_SCHEDULE_RESENDS = False

# If set to True, recipients will be able to text in to Cohorts by default
COHORT_ENABLEABLE_FROM_SMS = False

# If set to True, recipients can text in anything to become an active User, instead of needing to text an accepted start word (and without punctuation)
BYPASS_START_WORDS = False

#############################################
########## TECHNICAL SETTINGS !!! ###########
#############################################
# The number of threads to spawn when processing the main hourly task in entry_points.py
EVERY_HOUR_THREADCOUNT = 50

#############################################
############ OTHER FEATURES !!! #############
#############################################
# Path to where backups should be stored
BACKUPS_PATH = "/var/backups/mongo/"

#############################################
################ DO NOT MOVE ################
#############################################
# this imports deployment-specific settings to override default settings
from conf.settings_override import *
