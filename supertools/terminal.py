from pprint import pprint
from bson import ObjectId
from mongolia import list_database
from mongolia.mongo_connection import CONNECTION as conn

from utils.database import DatabaseCollection as DC, DatabaseObject as DO
from utils.server import PRODUCTION
from backend.incoming.entry_points import *
from backend.incoming.new_user import *
from backend.incoming.processing import *
from backend.outgoing.dispatcher import *
from backend.outgoing.exit_points import *
from conf.secure import TWILIO_TEST_ACCOUNT_SID, TWILIO_TEST_AUTH_TOKEN
from constants.database import ScheduleTypes, TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD, INTERNAL_SUPER_ADMIN_EMAIL
from database.backbone.cohorts import *
from database.backbone.schedules import *
from database.analytics.system_load import *
from database.analytics.responses import *
from database.tracking.access_codes import *
from database.tracking.admins import *
from database.tracking.messages import *
from database.tracking.schedule_execution import *
from database.tracking.users import *
from supertools.subclass_detector import all_children
from utils.time import datetime, timedelta, now
from utils.twilio_utils import TWILIO_CLIENT, twilio_send
from supertools.survey_reader import *

def make_sample_data():
    cohort = Cohort.get_test_cohort()
    schedule = Schedule.create(random_id=True, data={"subtype": ScheduleTypes.recurring, "send_hour": 19,
                    "resend_hour": 21, "cohort_id": cohort[ID_KEY], "question_days_of_week": [1,2,3]})
    question = Question.create({"text": "Is this a question?", 'cohort_id': cohort[ID_KEY]}, random_id=True)
    cohort.add_custom_attribute("Dave", "derp")
    for user in Users(cohort_id=ObjectId(cohort[ID_KEY])):
        user.add_custom_attribute("Dave", "derp")
    conditional = Conditional.create({"attribute": 'Dave', "comparison": 'dirk', "cohort_id": cohort[ID_KEY]}, random_id=True)
    schedule.add_action("send_question", {"database_id": question[ID_KEY]})
    schedule.add_action("send_message", {"text": "DAVE!"})
    schedule.add_action("conditional", {"database_id": conditional[ID_KEY]})
    schedule.add_action("set_attribute", {"attribute_name": 'Dave', "attribute_value": 'dirk'})

def ls(db=None):
    return list_database(db)

def deprecate(d):
    DC(d)._move("deprecated." + d)

def deprecate_big(d):
    shards = int(DC.count(d) / 100) + 1
    for _ in range(shards):
        DC(d, page_size=100)._move(d)

def reset_databases(are_you_sure=False):
    if PRODUCTION:
        return
    if are_you_sure:
        for Subclass in all_children(DatabaseCollection):
            for element in Subclass():
                element.remove()
    else:
        print "fwew, good thing I didn't type 'reset_database(True)' by accident"

def set_internal_super_admin_password(password):
    if password:
        Admin(email=INTERNAL_SUPER_ADMIN_EMAIL).set_password(password)
        print "You are the Special."
    else:
        print "Please input a password 'set_internal_super_admin_password(password)'."

def set_up_database(email, password):
    if not Customer(customer_name="Zagaran"):
        Customer.make_customer("Zagaran")
    Admin.make_admin(email, password, Customer(customer_name="Zagaran")[ID_KEY])

def print_databases():
    for Subclass in all_children(DatabaseCollection):
        print Subclass().__class__.__name__
        pprint(Subclass())
        print "\n--\n"

def counts(db):
    for i in ls(db):
        print(str(DC.count(db + "." + i)) + "\t" + db + "." + i)


def quick_shell():
    print("\n")
    print("DO = DatabaseObject")
    print("DC = DatabaseCollection")
    print("conn = Database Connection")
    print("test_user = Test User")
    print("super_admin = Super Admin")
    print("\n")
    print("Everything from sms, users, dispatch, incoming, detection, and access_codes has been imported.")
    try:
        print(ls())
        return True
    except Exception as e:
        print("\nWARNING: MONGO IS DOWN\n")
        print(repr(e))
        exit()


quick_shell()
if not PRODUCTION:
    # get test cohort
    test_cohort = Cohort.get_test_cohort()
    # get test user
    test_user = User.get_test_user()
# get internal super admin user
super_admin = Admin.get_internal_super_admin()
