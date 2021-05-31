from constants.users import Status

INC = "$inc"

INTERNAL_CUSTOMER_NAME = "Zagaran"
INTERNAL_SUPER_ADMIN_EMAIL = "support@instantcensus.com"
TEST_ADMIN_EMAIL = "test@instantcensus.com"
TEST_ADMIN_PASSWORD = " "
TEST_COHORT_NAME = "__Test__"
TEST_COHORT_PHONENUM = "+11111111111"

ANSWER_VALUE = "__ANSWER__"
ANSWER_VALUE_DISPLAY = "(ANSWER)"  # what shows up on the front end
SKIP_VALUE = "__SKIP__"
BAD_RESPONSE_LIMIT_REACHED_VALUE = "__BAD_RESPONSE_LIMIT_REACHED__"

EXCLUDE_DELETED_USERS_QUERY = {"$ne": Status.deleted}

class ScheduleTypes(object):
    recurring = "recurring"
    one_time = "one_time"
    daily_limit = "daily_limit"
    on_user_creation = "on_user_creation"
