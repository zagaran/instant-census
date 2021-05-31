from constants.exceptions import UnknownCohortError
from mongolia import ID_KEY

from app import app
from constants.users import Status
from database.tracking.admins import Admin
from database.tracking.users import User
from tests.common import InstantCensusTestCase, test_admin_log_in_response, \
    create_new_cohort_response, copy_survey_to_cohort_response
from constants.database import TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD, INTERNAL_CUSTOMER_NAME
from database.backbone.cohorts import Cohort, Cohorts, Customer


# Test surveys are for the copy_survey test in TestCohortsDashboard.
# The first test survey has attributes and is intended to fail; the second one should be successful.

test_survey_with_attributes = """header: cohort = __Test__; subtype = recurring; send_hour = 12; resend_hour = 14; resend_quantity = 5; question_period = 7
attributes: color = red; greeting = hello
question 1 {so hi, person!}
    if yes:
        set attribute color to blue
        question 2 {well then}
        if attribute color is blue:
            question 3 {really, [[COLOR]]?}
question 4 {last question}"""

test_survey = """header: cohort = __Test__; subtype = recurring; send_hour = 12; resend_hour = 14; resend_quantity = 5; question_period = 7
question 1 {hi, person!}
    if yes:
        question 2 {well then}
question 4 {last question}"""

class TestCohortsDashboard(InstantCensusTestCase):
    
    def test_cohorts_dashboard_actions(self):
        admin = Admin.get_test_admin()
        test_app = app.test_client()
        resp = test_admin_log_in_response(test_app)
        self.assertRedirect(resp, "Bad login.")
        
        # create_cohort()
        before = Cohorts.count()
        new_cohort_name = "__Test2__"
        resp = create_new_cohort_response(test_app, new_cohort_name)
        after = Cohorts.count()
        self.assertResponseOkay(resp, "Bad return status on /create_cohort")
        self.assertEqual(before + 1, after, "Create cohort via POST failed")
        self.assertTrue(Cohort.retrieve(cohort_name=new_cohort_name) != {}, "create_cohort failed; cohort not created")
        ###################################################################################
        # create_cohort() duplicate should fail
        before = Cohorts.count()
        resp = create_new_cohort_response(test_app, new_cohort_name)
        after = Cohorts.count()
        self.assertEqual(resp.status_code, 400, "Incorrect return status on duplicate /create_cohort")
        self.assertEqual(before, after, "Create duplicate cohort via POST succeeded when it shouldn't")
        ###################################################################################
        # modify_cohort()
        cohort_new = Cohort.retrieve(cohort_name=new_cohort_name)
        second_cohort_name = "__Test2v2__"
        resp = test_app.post("/modify_cohort", data={
            "cohort_id": cohort_new[ID_KEY],
            "cohort_name": second_cohort_name,
            "area_code": 987,
            "welcome_message": "bye",
            "inactive_limit": 2,
            "inactive_time_limit": 56
        })
        cohort_result = Cohort.retrieve(cohort_name=second_cohort_name)
        self.assertResponseOkay(resp, "Bad return status on /modify_cohort")
        self.assertRaisedException(
            Cohort.retrieve,
            UnknownCohortError,
            "/modify cohort created new cohort object instead of modifying",
            cohort_name=new_cohort_name
        )
        self.assertEqual(cohort_result["cohort_name"], second_cohort_name,
                         "Modify cohort via POST failed (name)")
        self.assertEqual(cohort_result["area_code"], 987,
                         "Modify cohort via POST failed (area code)")
        self.assertEqual(cohort_result["welcome_message"], "bye",
                         "Modify cohort via POST failed (welcome message)")
        self.assertEqual(cohort_result["inactive_limit"], 2,
                         "Modify cohort via POST failed (inactive limit)")
        
        # change_cohort_status()
        cohort = Cohort.retrieve(cohort_name=second_cohort_name)
        resp = test_app.post("/change_cohort_status", data={
            "cohort_id": cohort[ID_KEY],
            "new_value": "paused"
        })
        cohort_result = Cohort.retrieve(cohort_name=second_cohort_name)
        self.assertResponseOkay(resp, "Bad return status on /change_cohort_status")
        self.assertTrue(cohort_result["status"] == "paused", "/change_cohort_status failed")
        
        # modify_cohort() duplicate
        cohort = Cohort.retrieve(cohort_name=second_cohort_name)
        resp = test_app.post("/modify_cohort", data={
            "cohort_id": cohort[ID_KEY],
            "cohort_name": "__Test__",
            "area_code": 987,
            "welcome_message": "bye",
            "inactive_limit": 2
        })
        self.assertEqual(resp.status_code, 400, "Incorrect return status on /modify_cohort to a duplicate name")

        # copy_survey() unsuccessful case
        resp = copy_survey_to_cohort_response(test_app, second_cohort_name, test_survey_with_attributes)
        self.assertEqual(resp.status_code, 400, "Incorrect return status on /copy_survey")

        # copy_survey() successful case
        resp = copy_survey_to_cohort_response(test_app, second_cohort_name, test_survey)
        self.assertResponseOkay(resp, "Bad return status on /copy_survey")


        # delete_cohort() (doesn't actually delete, just marks it as deleted)
        cohort_before = Cohort.retrieve(cohort_name=second_cohort_name)
        resp = test_app.get("/delete/%s" % cohort_before[ID_KEY])
        self.assertRaisedException(
            Cohort.retrieve,
            UnknownCohortError,
            "Delete cohort via GET failed",
            cohort_name=second_cohort_name
        )
        self.assertResponseOkay(resp, "Bad return status on /delete/<cohort_id>")
