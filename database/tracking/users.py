from datetime import timedelta

from mongolia.constants import REQUIRED_STRING

from conf.settings import DISABLE_INACTIVE_STATUS, SHOW_DELETED_USERS
from constants.cohorts import CohortStatus
from constants.database import TEST_COHORT_PHONENUM, EXCLUDE_DELETED_USERS_QUERY
from constants.users import (Status, TEST_USER_PHONENUM)
from database.backbone.cohorts import Cohort, Cohorts
from database.tracking.messages import Messages
from database.tracking.user_messages import UserMessages
from utils.codes import generate_temp_pass
from utils.database import (DatabaseConflictError, DatabaseObject, DatabaseCollection, REQUIRED,
    ID_KEY, fast_live_untyped_iterator)
from utils.formatters import phone_format
from utils.logging import log_error
from utils.time import now


class User(DatabaseObject, UserMessages):
    PATH = "tracking.users"
    
    DEFAULTS = {
        "phonenum": REQUIRED_STRING,
        "cohort_id": REQUIRED,
        "ic_number": None,
        "status": Status.active,
        "status_log": [],
        "custom_attributes": {},
        "access_code": None,
        "current_execution": None,
        "needs_review": False,
        "onboarded": False,
        "timezone": "US/Eastern",
        "phonenum_status": None,  # e.g. to track for landlines
        
        "create_time": now,
        "modify_time": now, #TODO

    }

    @staticmethod
    def retrieve(include_deleted=False, **kwargs):
        # (phonenum, ic_number) tuple identifies users with the same phone number in different cohorts
        # (phonenum, cohort_id) looks for the user in the cohort
        if "phonenum" in kwargs:
            kwargs["phonenum"] = phone_format(kwargs["phonenum"])
        if "ic_number" in kwargs:
            kwargs["ic_number"] = phone_format(kwargs["ic_number"])
        if not SHOW_DELETED_USERS:
            kwargs["status"] = EXCLUDE_DELETED_USERS_QUERY
        users = Users(**kwargs)
        if len(users) == 1:
            return users[0]
        elif len(users) > 1:
            raise DatabaseConflictError("Multiple users were found for User.retrieve() query:\n\n %s" % kwargs)
        return None
    
    @staticmethod
    def get_test_user():
        try:
            cohort = Cohort.get_test_cohort(activate=False)
            user = User.create(TEST_USER_PHONENUM, cohort[ID_KEY])
            user["custom_attributes"] = cohort["custom_attributes"]
            user.save()
        except DatabaseConflictError:
            pass
        return User.retrieve(phonenum=TEST_USER_PHONENUM, ic_number=TEST_COHORT_PHONENUM)
    
    # @staticmethod
    # def get_admin_user():
    #     try:
    #         User.create(ADMIN_USER_PHONENUM, Cohort.get_test_cohort(False)[ID_KEY])
    #     except DatabaseConflictError:
    #         pass
    #     user = User.retrieve_by_cohort(ADMIN_USER_PHONENUM, Cohort.get_test_cohort(False)[ID_KEY])
    #     user["admin"] = AdminTypes.standard
    #     user.save()
    #     return user

    @classmethod
    def create(cls, phonenum, cohort_id, status=Status.active):
        phonenum = phone_format(phonenum)
        cohort = Cohort(cohort_id)
        ic_number = cohort.get_ic_number()  # returns None if over COHORT_USER_LIMIT
        # list comprehension to check for existing user that isn't deleted; next line is previous code
        # if cls.exists(cohort_id=cohort_id, phonenum=phonenum):
        kwargs = {
            "cohort_id": cohort_id,
            "phonenum": phonenum,
            "status": EXCLUDE_DELETED_USERS_QUERY,
        }
        if Users.count(**kwargs):
            raise DatabaseConflictError("A user with phone number %s already exists." % phonenum)
        if cohort.over_capacity():
            status = Status.waitlist
        new_user = {
            "cohort_id": cohort[ID_KEY],
            "custom_attributes": cohort["custom_attributes"],
            "ic_number": ic_number,
            "phonenum": phonenum,
            "status": status,
            "status_log": [[status, now()]]
        }
        user = super(User, cls).create(new_user, random_id=True)
        user.update_schedule_executions(now())
        return user
    
    def is_active(self):
        return self.status == Status.active

    def cohort_is_active(self):
        return self.get_cohort()["status"] == CohortStatus.active

    def update_schedule_executions(self, curr_time):
        """ Creates new Schedule executions from new schedules """
        from database.tracking.schedule_execution import (ScheduleExecution,
            ScheduleExecutions)
        user_schedules = [s["schedule_id"] for s in ScheduleExecutions(user_id=self[ID_KEY])]
        cohort = self.get_cohort()
        schedule_ids = [s[ID_KEY] for s in cohort.get_active_schedules()]
        for schedule_id in schedule_ids:
            if schedule_id not in user_schedules:
                ScheduleExecution.make_execution(self, schedule_id, curr_time)
    
    def new_password(self):
        passwd = generate_temp_pass()
        self["temp_pass"] = passwd
        self["temp_pass_expiration"] = now() + timedelta(hours=5)
        self.save()
        return passwd
    
    def has_password(self):
        return self["temp_pass"] is not None and self["temp_pass_expiration"] > now()
    
    def check_password(self, password):
        return self.has_password() and self["temp_pass"] == password.upper()
    
    def set_status(self, status):
        if status == self["status"]:
            # no changes needed
            return
        if DISABLE_INACTIVE_STATUS and status == Status.inactive:
            status = Status.completed
        # if user was originally deleted and there's a user that had been created with the same phonenum and cohort
        # that's not deleted
        if self["status"] == Status.deleted and User.retrieve(phonenum=self["phonenum"], cohort_id=self["cohort_id"]):
            raise DatabaseConflictError("An active user with phone number '%s' already exists." % self["phonenum"])
        # update status log
        try:
            self["status_log"].append([status, now()])
        except Exception as e:
            log_error(e, "error in set_status")
        # change status
        self["status"] = status
        # remove executions if user is not active
        if status != Status.active:
            self.clear_executions()
        self.save()

    def clear_executions(self):
        from database.tracking.schedule_execution import ScheduleExecutions
        for schedule_execution in ScheduleExecutions(user_id=self[ID_KEY]):
            schedule_execution.update(active=False, execution_state=None)
        self.update(current_execution=None)

    def get_cohort(self):
        return Cohort(self["cohort_id"])
    
    def get_unhandled_message_count(self):
        return Messages.count(user_id=self._id, needs_review=True)
    
    def display_phonenum(self):
        return ('-'.join((self["phonenum"][:5], self["phonenum"][5:8], self["phonenum"][8:])))[2:]

    def add_custom_attribute(self, new_attribute, default_value):
        self["custom_attributes"][new_attribute] = default_value
        self.save()


class Users(DatabaseCollection):
    OBJTYPE = User
    
    @staticmethod
    def active(**kwargs):
        active_cohorts_ids = Cohorts.active(field=ID_KEY)
        # modified to be a generator
        return Users.iterator(status=Status.active, cohort_id={"$in": active_cohorts_ids}, **kwargs)
    
    @classmethod
    def get_for_cohort_object_id(cls, cohort_id, iterator=False, **kwargs):
        kwargs["cohort_id"] = cohort_id
        # remove deleted users unless deleted flag is true
        if not SHOW_DELETED_USERS:
            kwargs["status"] = EXCLUDE_DELETED_USERS_QUERY
        if iterator:
            return fast_live_untyped_iterator(cls, **kwargs)
        else:
            return cls(**kwargs)

    @classmethod
    def get_count_for_cohort_object_id(cls, cohort_id, **kwargs):
        kwargs["cohort_id"] = cohort_id
        # remove deleted users unless deleted flag is true
        if not SHOW_DELETED_USERS:
            kwargs["status"] = EXCLUDE_DELETED_USERS_QUERY
        return cls.count(**kwargs)
    