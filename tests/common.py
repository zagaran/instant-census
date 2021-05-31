from mock import patch
from mongolia import MongoliaTestCase, ID_KEY
from app import app
from constants.database import TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD, ScheduleTypes
from constants.users import Status
from database.backbone.cohorts import Customer, Cohort
from database.backbone.schedules import Schedule, Schedules
from database.tracking.admins import Admin
from database.tracking.users import User
from supertools.survey_reader import compile_survey
from utils.server import get_twilio_client_testing
from utils.time import zero_day

class InstantCensusTestCase(MongoliaTestCase):
    
    @patch("utils.twilio_utils.get_twilio_client", side_effect=get_twilio_client_testing)
    def setUp(self, _mock):
        self.set_test_items()
    
    def set_test_items(self):
        """
        Sets self.customer, test_cohort, test_app, test_user, admin
        """
        app.config["TESTING"] = True

        # create customer
        self.customer = Customer.get_internal_customer()

        # create test admin
        self.admin = Admin.get_test_admin()

        # create test user
        self.test_user = User.get_test_user()
        self.test_user.set_status(Status.active)

        # get test cohort
        self.test_cohort = Cohort.get_test_cohort()

        # login admin
        self.test_app = app.test_client()
        resp = self.test_app.post("/login", data={"email": TEST_ADMIN_EMAIL,
                                                  "password": TEST_ADMIN_PASSWORD})
        self.assertRedirect(resp, "Bad login")

    def assertResponseOkay(self, http_response, msg):
        self.assertTrue(http_response.status_code < 400, msg)
    
    def assertRaisedException(self, func, exception, msg, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception as e:
            self.assertTrue(isinstance(e, exception), msg)
    
    def assertHasContent(self, response, content, msg):
        self.assertTrue(content in response.data, msg)
    
    def assertRedirect(self, response, msg):
        self.assertTrue(response.status_code == 302, msg)

################################################################

# def create_one_time_schedule(start_time):
#     """ function for creating one-time schedule """
#     test_cohort_id = Cohort.get_test_cohort()[ID_KEY]
#     schedule = Schedule.create(
#         {"cohort_id": test_cohort_id, "subtype": ScheduleTypes.one_time,
#          "send_hour": start_time.hour, "date": zero_day(start_time)},
#         random_id=True
#     )
#     return schedule

def test_admin_log_in_response(test_app):
    resp = test_app.post("/login", data={"email": TEST_ADMIN_EMAIL,
                                             "password": TEST_ADMIN_PASSWORD})
    return resp

def create_new_cohort_response(test_app, new_cohort_name, area_code=123, welcome_message="hi", inactive_limit=1, inactive_time_limit=0):
    resp = test_app.post("/create_cohort", data={
        "cohort_name": new_cohort_name,
        "area_code": area_code,
        "welcome_message": welcome_message,
        "inactive_limit": inactive_limit,
        "inactive_time_limit": inactive_time_limit
    })
    return resp

def copy_survey_to_cohort_response(test_app, destination_cohort_name, uncompiled_survey):
    destination_cohort = Cohort.retrieve(cohort_name=destination_cohort_name)
    compile_survey(uncompiled_survey)
    survey_object = Schedules()[-1]
    schedule_id_to_copy = survey_object[ID_KEY]
    resp = test_app.post("/copy_survey", data={
        "schedule_id": schedule_id_to_copy,
        "new_cohort_id": destination_cohort[ID_KEY]
    })
    return resp
