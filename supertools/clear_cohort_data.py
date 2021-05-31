from mongolia.constants import ID_KEY

from bson.objectid import ObjectId

from backend.admin_portal.common_helpers import validate_cohort, validate_user
from database.analytics.responses import Responses
from database.backbone.cohorts import Cohort
from database.backbone.schedules import Schedules
from database.tracking.messages import Messages, ControlMessages
from database.tracking.schedule_execution import ScheduleExecutions
from database.tracking.users import Users


def clear_cohort_data(cohort_id):
    cohort = validate_cohort(cohort_id)
    # remove users and user executions, responses, messages, and control messages
    for user in Users(cohort_id=cohort[ID_KEY]):
        clear_user_data(user[ID_KEY])
    # remove schedules
    for sched in Schedules(cohort_id=cohort[ID_KEY]):
        sched.recursive_delete()
    # remove cohort custom attributes
    cohort["custom_attributes"].clear()
    
def clear_user_data(user_id):
    user = validate_user(user_id)
    # remove user and user executions, responses, messages, and control messages
    for execution in ScheduleExecutions(user_id=user[ID_KEY]):
        execution.remove()
    for response in Responses(user_id=user[ID_KEY]):
        response.remove()
    for message in Messages(user_id=user[ID_KEY]):
        message.remove()
    for control in ControlMessages(user_id=user[ID_KEY]):
        control.remove()
    user.remove()