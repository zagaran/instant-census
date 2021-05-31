from mongolia.constants import ID_KEY
from datetime import datetime

from constants.database import ScheduleTypes
from database.tracking.users import User
from database.backbone.schedules import Schedule, Question
from utils.database import DatabaseObject, DatabaseCollection, REQUIRED, DatabaseConflictError
from utils.logging import log_warning
from utils.time import zero_day, timedelta, days_in_question_period, resend_times, convert_from_utc, now, convert_to_utc


class ScheduleExecution(DatabaseObject):
    PATH = "tracking.schedule_execution"
    DEFAULTS = {
        "user_id": REQUIRED,
        "schedule_id": REQUIRED,
        "current_period_start": datetime.min, # stored in abstract time
        "current_period_end": datetime.min, # stored in abstract time
        "resend_times": [], # stored in local time, not UTC
        "active": False,
        "execution_state": None, # [schedule_id, action_id, action_id, action_id, ...]
        "create_time": now,
        "modify_time": now, # TODO
    }
    
    @classmethod
    def make_execution(cls, user, schedule_id, curr_time):
        data = {"user_id": user[ID_KEY], "schedule_id": schedule_id}
        if cls.exists(data):
            raise DatabaseConflictError("A ScheduleExecution already exists for %s" % data)
        # create execution
        ret = cls.create(data, random_id=True)
        # set execution periods
        ret.set_period(curr_time)
        # set execution active to False
        ret.update(active=False)
        return ret[ID_KEY]
    
    def get_schedule(self):
        return Schedule(self["schedule_id"])
    
    def get_question(self):
        if not self["execution_state"]:
            return None
        # The last node of the execution state will always be a question,
        # unless new actions that wait for user response are added
        return Question(self["execution_state"][-1])
    
    def run(self, curr_time, parser_return=None, resend=False, manual_run=False, delay=True):
        """ Return true if schedule has paused for user input """
        user = User(self["user_id"])
        curr_time = convert_from_utc(curr_time, user["timezone"])
        if not manual_run:
            if self["current_period_end"] and curr_time > self["current_period_end"]:
                # Don't continue running expired schedules
                return False
        user = User(self["user_id"])
        if not user or not user.is_active() or not user.cohort_is_active():
            log_warning("Bad ScheduleExecution \"%s\" found; no matching user" % self[ID_KEY])
            return False
        # make sure schedule exists and isn't deleted
        schedule = self.get_schedule()
        if not schedule or schedule["deleted"]:
            log_warning("Bad ScheduleExecution \"%s\" found; no matching schedule" % self[ID_KEY])
            return False
        if schedule["cohort_id"] != user["cohort_id"]:
            log_warning("Bad ScheduleExecution \"%s\" found; mismatched cohort id for schedule and user" % self[ID_KEY])
            return False
        # Set user's current execution here so it is available data while running
        user.update(current_execution=self[ID_KEY])
        execution_state = self["execution_state"] or []
        if not execution_state:
            resend = False
        ret = schedule.do_actions(user, parser_return, execution_state,
                                  resend=resend, delay=delay)
        if ret:
            self.update(execution_state=ret, active=True)
            return True
        else:
            self.update(execution_state=None, active=False)
            user.update(current_execution=None)
            return False

    def set_period(self, curr_time, update=False):
        """ Return true if set_period has set the schedule to active """
        user = User(self["user_id"])
        curr_time = convert_from_utc(curr_time, user["timezone"])
        active = True
        # if update is set, skip check and set period
        if update:
            # if the current execution is active, we don't want to update yet
            if self["active"]:
                return False
            active = False
        elif not self["current_period_end"] or curr_time < self["current_period_end"]:
            # Schedule has expired or is still in a survey period
            return False
        schedule = self.get_schedule()
        if not schedule:
            return False
        if schedule["subtype"] == ScheduleTypes.one_time:
            return_value = self.set_one_time_period(curr_time, schedule, active=active)
        elif schedule["subtype"] == ScheduleTypes.recurring:
            return_value = self.set_recurring_period(curr_time, schedule, active=active)
        elif schedule["subtype"] == ScheduleTypes.daily_limit:
            return_value = self.set_daily_limit_period(curr_time, schedule, active=active)
        elif schedule["subtype"] == ScheduleTypes.on_user_creation:
            return_value = self.set_on_user_creation(curr_time, schedule)
        else:
            raise Exception("Unsupported schedule subtype %s" % schedule["subtype"])
        return return_value
    
    def set_one_time_period(self, curr_time, schedule, active):
        date = schedule["date"]
        start_time = date.replace(hour=schedule["send_hour"])
        if curr_time >= start_time:
            # Sets current_period_end to None, indicating schedule has expired
            resends = resend_times(curr_time, start_time, schedule['resend_hour'],
                                   schedule['resend_quantity'], schedule['resend_type'])
            self.update(current_period_start=start_time, current_period_end=None,
                        resend_times=resends, execution_state=None, active=active)
            return active
        # Update date in case schedule has changes
        self.update(current_period_end=start_time, resend_times=[])
        return False
    
    def set_recurring_period(self, curr_time, schedule, active):
        # Get the starting time for the current period
        period_start = zero_day(curr_time) + timedelta(hours=schedule["send_hour"])
        if curr_time < period_start:
            period_start -= timedelta(days=1)

        # Gets the number of days for the current period
        if not schedule["question_days_of_week"]:
            days_diff = schedule["question_period"]
        else:
            days_diff = days_in_question_period(period_start,
                                                schedule["question_days_of_week"])
        period_end = period_start + timedelta(days=days_diff)
        resends = resend_times(curr_time, period_start, schedule['resend_hour'],
                               schedule['resend_quantity'], schedule['resend_type'])
        self.update(current_period_start=period_start, current_period_end=period_end,
                    resend_times=resends, execution_state=None, active=active)
        return active
    
    def set_daily_limit_period(self, curr_time, schedule, active):
        period_start = zero_day(curr_time) + timedelta(hours=schedule["send_hour"])
        period_end = period_start + timedelta(weeks=5000)
        resends = resend_times(curr_time, period_start, schedule['resend_hour'],
                               schedule['resend_quantity'], schedule['resend_type'], daily_limit=True)
        self.update(current_period_start=period_start, current_period_end=period_end,
                    resend_times=resends, execution_state=None, active=active)
        return active
    
    def set_on_user_creation(self, curr_time, schedule):
        resends = resend_times(curr_time, curr_time, schedule['resend_hour'],
                               schedule['resend_quantity'], schedule['resend_type'])
        # TODO: setting current_period_start here fixes issue with retrieving the correct Response
        # object, but may potentially break other things (like daily limit questions)
        self.update(current_period_start=curr_time, current_period_end=None, resend_times=resends,
                    execution_state=None, active=False)
        return False
    
    def check_resend(self, curr_time):
        user = User(self["user_id"])
        curr_time = convert_from_utc(curr_time, user["timezone"])
        if not self["resend_times"] or not self["active"]:
            return False
        if self["current_period_end"] and self["current_period_end"] < curr_time:
            return False
        if self["resend_times"][0] <= curr_time:
            # schedule = self.get_schedule()
            # if schedule['subtype'] == 'daily_limit':
                # TODO: fix this when making daily_limits work
                # resend = self["resend_times"][4]
                # resend += timedelta(days=schedule["question_period"])
                # self["resend_times"].append(resend)
            new_resend_times = [i for i in self["resend_times"] if i > curr_time]
            self.update(resend_times=new_resend_times)
            return True
        return False

class ScheduleExecutions(DatabaseCollection):
    OBJTYPE = ScheduleExecution


