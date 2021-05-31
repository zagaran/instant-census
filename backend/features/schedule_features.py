from mongolia.constants import ID_KEY
from conf.settings import STOP_INTERRUPTED_SCHEDULE_RESENDS
from database.tracking.schedule_execution import (ScheduleExecutions,
    ScheduleExecution)
from constants.database import ScheduleTypes
from database.backbone.schedules import Schedules
from utils.logging import log_error

"""
A schedule is the root of a tree of action nodes.  An ActionNode is a Mongolia
object and has a list of ActionConfigs that are the actions for that node.
Current types of ActionNodes include Schedules, Questions, and Conditionals.
Questions and Conditionals form the body of the tree, since they are both
actions themselves, as well as can have other actions follow from them.

An ActionConfig is a python dictionary that specifies an action function and
any extra parameters that function needs. ActionConfigs are created by and used
by the ActionConfig class in utils.actions.

An action function is a function in backend.actions.actions that has the
@Action decoration.  The arguments to that function are passed by a combination
of the params specified in the ActionConf (static params, like a database id)
and the state of the system at the time it's called (dynamic params, like the
current user or the current execution state).

When a schedule is run, the tree of action nodes is traversed via depth first
search.  If at any point the execution pauses for user input (which currently
only happens when it sends a question), the current chain of nodes in the tree
is saved as the "execution state" on a ScheduleExecution Mongolia object, and
that ScheduleExecution is set as the current_execution on the user.  This is
all so that when a user responds, or if a user fails to respond by one of the
resend times, we can resume execution of the tree from where we left off.
"""

def run_schedules(user, curr_time, delay=True):
    """ This function is called from every_hour.
        It runs schedules that have just been set to active until a question is
        sent.  Then, it continues setting schedules to active but doesn't run
        them (that will happen in run_outstanding_schedules). """
    sent_question = False
    user.update_schedule_executions(curr_time)
    executions = ScheduleExecutions(user_id=user[ID_KEY])
    for execution in executions:
        set_period = execution.set_period(curr_time)
        if not sent_question:
            if execution.check_resend(curr_time):
                if execution.run(curr_time, resend=True, delay=delay):
                    sent_question = True
        if set_period and not sent_question:
            if execution.run(curr_time, delay=delay):
                sent_question = True
        # this will update non-active executions to maintain consistency between
        # schedule and schedule execution parameters
        execution.set_period(curr_time, update=True)
    return sent_question


def run_outstanding_schedules(user, curr_time, delay=True):
    """ This function is called from on_receive.
        It is called after the user has finished running their current schedule
        and goes through running other schedules that are currently active
        for that user until a question is sent. """
    # TODO: prioritize active executions that already have an execution state
    if STOP_INTERRUPTED_SCHEDULE_RESENDS:
        return False
    executions = ScheduleExecutions(user_id=user[ID_KEY], active=True)
    for execution in executions:
        if execution.run(curr_time, resend=True, delay=delay):
            return True
    return False


def run_on_user_creation_schedules(user, curr_time, delay=True):
    """ This function is run on user creation.
        It sets all on_create schedules for that user to active (this is the
        only place that on_create schedules get set to active) and runs
        on_create schedules until a question is sent. """
    user.update_schedule_executions(curr_time)
    executions = [ScheduleExecution(schedule_id=s[ID_KEY], user_id=user[ID_KEY])
                  for s in Schedules(cohort_id=user["cohort_id"],
                                     subtype=ScheduleTypes.on_user_creation,
                                     deleted=False)]
    sent_question = False
    for execution in executions:
        try:
            execution.update(active=True)
            if not sent_question:
                if execution.run(curr_time, delay=delay):
                    sent_question = True
        except Exception as e:
            # TODO: find out why execution does not exist for schedule (executions == [{}, {REALEXECUTIONOBJECT}])
            log_error(e, "run_on_user_creation_schedules() encountered error for user %s" % user[ID_KEY], curr_time)
