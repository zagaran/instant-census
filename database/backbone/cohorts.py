from conf.settings import SHOW_DELETED_USERS, COHORT_USER_LIMIT, COHORT_ENABLEABLE_FROM_SMS
from mongolia.constants import REQUIRED_STRING

from constants import messages
from constants.cohorts import CohortStatus, PHONENUM_USER_LIMIT
from constants.database import TEST_COHORT_PHONENUM, INTERNAL_CUSTOMER_NAME, TEST_COHORT_NAME, \
    EXCLUDE_DELETED_USERS_QUERY
from constants.exceptions import UnknownCohortError
from constants.users import Status
from database.backbone.schedules import Schedules
from database.tracking.messages import Messages, ControlMessages
from utils.database import (DatabaseObject, DatabaseCollection, REQUIRED, ID_KEY,
    DatabaseConflictError)
from utils.logging import log_error
from utils.server import PRODUCTION
from utils.time import now
from utils.twilio_utils import create_new_phonenum


class Customer(DatabaseObject):
    PATH = "backbone.customers"
    DEFAULTS = {
        "customer_name": REQUIRED_STRING,
        "message_limit": 250000,
        "message_limit_expiration": now,
        "create_time": now,
        "modify_time": now,  # TODO

    }

    @classmethod
    def make_customer(cls, customer_name, message_limit=250000, message_limit_expiration=now()):
        new_customer = {
            "customer_name": customer_name,
            "message_limit": message_limit,
            "message_limit_expiration": message_limit_expiration
        }
        customer = cls.create(new_customer, random_id=True)
        return customer

    def get_total_message_count(self):
        cohorts = Cohorts(customer_id=self[ID_KEY])
        return sum(cohort.get_total_message_count() for cohort in cohorts)

    @staticmethod
    def get_internal_customer():
        customer = Customer(customer_name=INTERNAL_CUSTOMER_NAME)
        if not customer:
            customer = Customer.make_customer(INTERNAL_CUSTOMER_NAME)
        return customer

class Customers(DatabaseCollection):
    OBJTYPE = Customer


# To represent a block of affiliated users
# example: all patients from same practice, insurance company, etc
class Cohort(DatabaseObject):
    PATH = "backbone.cohorts"
    DEFAULTS = {
        # ID_KEY is cohort name
        "customer_id": REQUIRED,
        "ic_numbers": [],
        "cohort_name": REQUIRED_STRING,
        "admin_id": None,

        # Cohort configuration
        "status": CohortStatus.pending,
        "status_log": [],
        "enableable_from_sms": COHORT_ENABLEABLE_FROM_SMS,
        "pending_message": messages.DEFAULT_PENDING,
        "waitlist_message": messages.DEFAULT_WAITLIST,
        "welcome_message": messages.DEFAULT_WELCOME_CUSTOMIZABLE,
        "problem_message": None,
        "free_report_response": None,
        "inactive_limit": 5,  # num of unanswered questions before user set to inactive
        "inactive_time_limit": 0, # num of hours without user response before user set to inactive
        "access_code_required": False,
        "size_limit": None,
        "reactivate_allowed": True,
        "custom_attributes": {},
        "area_code": None,

        "create_time": now,
        "modify_time": now,  # TODO

    }
    
    @classmethod
    def create(cls, cohort_name, customer_id, status=CohortStatus.pending, admin_id=None):
        assert Customer.exists(customer_id), "Customer does not exist in Customers()"
        return super(Cohort, cls).create({
            "cohort_name": cohort_name,
            "customer_id": customer_id,
            "admin_id": admin_id,
            "status_log": [[status, now()]]
        }, random_id=True)
    
    @staticmethod
    def retrieve(include_deleted=False, **kwargs):
        cohorts = Cohorts(**kwargs)
        if not include_deleted:
            cohorts = [u for u in cohorts if u["status"] != CohortStatus.deleted]
        if len(cohorts) == 1:
            return cohorts[0]
        elif len(cohorts) > 1:
            raise DatabaseConflictError("Multiple cohorts were found for Cohort.retrieve() query:\n\n %s" % kwargs)
        raise UnknownCohortError()

    @staticmethod
    def get_test_cohort(activate=True):
        customer = Customer(customer_name=INTERNAL_CUSTOMER_NAME)
        if not customer:
            try:
                customer = Customer.make_customer(INTERNAL_CUSTOMER_NAME)
            except DatabaseConflictError:
                pass
        try:
            cohort = Cohort.retrieve(cohort_name=TEST_COHORT_NAME)
        except UnknownCohortError:
            cohort = Cohort.create(TEST_COHORT_NAME, customer[ID_KEY])
        cohort.update(ic_numbers=[TEST_COHORT_PHONENUM])
        if activate:
            cohort.set_status(CohortStatus.active)
        return cohort

    def is_initiated(self):
        return self["status"] in [CohortStatus.active, CohortStatus.paused]

    def get_active_users(self):
        # not global import to prevent cyclic import with Users
        from database.tracking.users import Users
        return Users(cohort_id=self[ID_KEY], status=Status.active)
    
    def get_active_schedules(self):
        return Schedules(cohort_id=self[ID_KEY], deleted=False)
    
    def get_active_user_count(self):
        # not global import to prevent cyclic import with Users
        from database.tracking.users import Users
        return Users.count(cohort_id=self._id, status=Status.active)

    def get_total_user_count(self):
        # not global import to prevent cyclic import with Users
        from database.tracking.users import Users
        users_filter_kwargs = {
            "cohort_id": self["_id"]
        }
        if not SHOW_DELETED_USERS:
            users_filter_kwargs["status"] = EXCLUDE_DELETED_USERS_QUERY
        return Users.count(**users_filter_kwargs)

    def get_unhandled_user_count(self):
        # not global import to prevent cyclic import with Users
        from database.tracking.users import Users
        return Users.count(cohort_id=self._id, status=Status.active, needs_review=True)
    
    def get_ic_number(self):
        # not global import to prevent cyclic import with Users
        from database.tracking.users import Users
        if not PRODUCTION:
            return TEST_COHORT_PHONENUM
        # TODO: move this up if we want to test this status in tests
        if self["status"] == CohortStatus.pending:
            return None
        if COHORT_USER_LIMIT:
            if Users.count(cohort_id=self[ID_KEY]) >= COHORT_USER_LIMIT:
                return None
        for ic_number in self["ic_numbers"]:
            if Users.count(ic_number=ic_number, status=Status.active) < PHONENUM_USER_LIMIT:
                return ic_number
        # if no existing number is under capacity, purchase new one
        # Twilio friendly name is limited to 64 characters
        customer_name = Customer(self.customer_id)["customer_name"]
        friendly_name = "%s~%s" % (customer_name, self.cohort_name)
        new_ic_number = create_new_phonenum(friendly_name[:65], self.area_code)
        #TODO race condition here when multiple threads saving on cohort.ic_numbers
        self["ic_numbers"].append(new_ic_number)
        self.save()
        return new_ic_number
    
    def get_total_message_count(self):
        cohort = Cohort(self[ID_KEY])
        total = Messages.count(ic_number={'$in': cohort["ic_numbers"]})
        total += ControlMessages.count(ic_number={'$in': cohort["ic_numbers"]})
        return total
    
    def over_capacity(self):
        # not global import to prevent cyclic import with Users
        from database.tracking.users import Users
        if self["size_limit"] is None:
            return False
        return Users.count(cohort_id=self[ID_KEY]) >= self["size_limit"]
    
    def get_access_codes(self, field=None):
        from database.tracking.access_codes import AccessCodes
        return AccessCodes(cohort_id=self[ID_KEY], field=field)
    
    def add_custom_attribute(self, new_attribute, default_value):
        self["custom_attributes"][new_attribute] = default_value
        self.save()
    
    def get_custom_attributes(self):
        """ Use this method to get cohort's custom attributes for processing.
            Custom attributes are stored lowered for processing and displayed upper-ed in interface. """
        return self["custom_attributes"]
    
    def generate_access_codes(self, num):
        from database.tracking.access_codes import AccessCode, generate_unique_code
        codes = []
        for _ in range(num):
            codes.append(AccessCode.create({ID_KEY: generate_unique_code(), "cohort_id": self[ID_KEY]}))
        return codes
    
    def serialized_schedules(self):
        return [s.serialize() for s in self.get_active_schedules()]

    def set_status(self, new_status):
        previous_status = self["status"]
        if new_status == previous_status:
            # no changes needed
            return
        # update status log
        try:
            self["status_log"].append([new_status, now()])
        except Exception as e:
            log_error(e, "error in set_status")
        # change status
        self["status"] = new_status
        self.save()
        # if we're activating the cohort for the first time, assign IC numbers
        if previous_status == CohortStatus.pending and new_status == CohortStatus.active:
            from database.tracking.users import Users
            for user in Users(cohort_id=self[ID_KEY], ic_number=None):
                user.update(ic_number=self.get_ic_number())
    
    def remove_needs_review(self):
        from database.tracking.users import Users
        for user in Users(cohort_id=self[ID_KEY]):
            if not user["needs_review"]:
                continue
            user.update(needs_review=False)
            for message in Messages(user_id=user[ID_KEY]):
                if not message["needs_review"]:
                    continue
                message.update(needs_review=False)


class Cohorts(DatabaseCollection):
    OBJTYPE = Cohort
    
    @staticmethod
    def active(**kwargs):
        """ Only called in Users.active(), just making it an iterator """
        return Cohorts(status=CohortStatus.active, **kwargs)
    
    @staticmethod
    def retrieve_by_customer(customer_id):
        if PRODUCTION:
            return [cohort for cohort in Cohorts(customer_id=customer_id) if
                    cohort["status"] != CohortStatus.deleted and
                    cohort["cohort_name"] != TEST_COHORT_NAME]
        else:
            return [cohort for cohort in Cohorts(customer_id=customer_id) if
                    cohort["status"] != CohortStatus.deleted]
    
    @staticmethod
    def retrieve_by_admin(admin_id):
        if PRODUCTION:
            return [cohort for cohort in Cohorts(admin_id=admin_id) if
                    cohort["status"] != CohortStatus.deleted and
                    cohort["cohort_name"] != TEST_COHORT_NAME]
        else:
            return [cohort for cohort in Cohorts(admin_id=admin_id) if
                    cohort["status"] != CohortStatus.deleted]
