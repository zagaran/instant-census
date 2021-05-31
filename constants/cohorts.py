from conf.settings import TIMEZONE_SUPPORT
from constants.parser_consts import SYSTEM_WORDS

PHONENUM_USER_LIMIT = 50

COHORT_STATUSES = ['active', 'pending', 'paused', 'deleted', 'completed']
class CohortStatus(object):
    active = "active"      # enabled
    pending = "pending"    # waiting for activation
    paused = "paused"      # temporarily suspended by admin
    deleted = "deleted"    # deleted by admin
    completed = "completed"  # marked as completed by admin


CONDITIONAL_SUBTYPES = ['exactly', 'greater', 'less', 'range']
class ConditionalSubtype(object):
    exactly = "exactly"
    greater = "greater"
    less = "less"
    range = "range"
    
RESEND_SUBTYPES = ["hours", "time", "none"]
class ResendSubtype(object):
    hours = "hours"
    time = "time"
    none = "none"


FORBIDDEN_CUSTOM_ATTRIBUTES = ["phonenumber", "phonenum", "status", "timezone"] + SYSTEM_WORDS
ALLOWED_USER_UPLOAD_ATTRIBUTES = ["timezone"]