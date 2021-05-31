from mongolia import ID_KEY

from app import app
from constants.users import Status
from database.backbone.schedules import Schedule, Question
from database.tracking.admins import Admin
from database.tracking.users import User
from tests.common import InstantCensusTestCase
from constants.database import (TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD,
    INTERNAL_CUSTOMER_NAME, ScheduleTypes)
from database.backbone.cohorts import Cohort, Customer

class TestPages(InstantCensusTestCase):
    
    def setUp(self):
        self.set_test_items()
        test_cohort_id = Cohort.get_test_cohort()[ID_KEY]
        ###################################################################################
        # Recurring schedule
        schedule1 = Schedule.create(
            {"cohort_id": test_cohort_id, "subtype": ScheduleTypes.recurring,
             "send_hour": 12, "resend_hour": 14, "resend_quantity": 5,
             "question_period": 7},
            random_id=True
        )
        question = Question.create(
            {"cohort_id": test_cohort_id, "text": "hi"}, random_id=True
        )
        schedule1.add_action("send_question", {"database_id": question[ID_KEY]})
        schedule1.add_action("send_question", {"database_id": question[ID_KEY]})
    
    def test_admin_portal_pages(self):
        resp = self.test_app.post("/login", data={"email": "junk",
                                             "password": "junk"})
        self.assertHasContent(resp, "Email or password is incorrect.", "Bad login succeeded.")
        resp = self.test_app.post("/login", data={"email": TEST_ADMIN_EMAIL,
                                             "password": TEST_ADMIN_PASSWORD})
        self.assertRedirect(resp, "Bad login.")
        cohort = Cohort.get_test_cohort()
        resp = self.test_app.get("/cohorts")
        self.assertResponseOkay(resp, "Bad return status on cohorts")
        resp = self.test_app.get("/%s/users" % cohort[ID_KEY])
        self.assertResponseOkay(resp, "Bad return status on users")
        resp = self.test_app.get("/%s/surveys" % cohort[ID_KEY])
        self.assertResponseOkay(resp, "Bad return status on survey builder")
        resp = self.test_app.get("/review")
        self.assertResponseOkay(resp, "Bad return status on needs review")
        user = User.get_test_user()
        resp = self.test_app.get("/%s/send/%s" % (cohort[ID_KEY], user[ID_KEY]))
        self.assertResponseOkay(resp, "Bad return status on message sender")
        actions = cohort.serialized_schedules()[0]["actions"]
        self.assertEqual(len(actions), 2, "Actions not properly serialized 1")
        self.assertEqual(bool(actions[0]), True, "Actions not properly serialized 2")
        self.assertEqual(bool(actions[1]), True, "Actions not properly serialized 3")
        resp = self.test_app.post("/logout")
        self.assertResponseOkay(resp, "Unable to log out.")

        

        # resp = self.test_app.get("/data")
        # self.assertResponseOkay(resp, "Bad return status on data reports")
        # self.assertEqual(resp.status, 404, "Bad return status expected on data reports")
