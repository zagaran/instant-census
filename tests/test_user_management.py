from StringIO import StringIO
from mongolia import ID_KEY

from app import app
from backend.admin_portal.user_managment_helpers import parse_uploaded_user_file
from constants.users import Status
from database.tracking.admins import Admin
from database.tracking.users import User
from tests.common import InstantCensusTestCase
from constants.database import TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD, INTERNAL_CUSTOMER_NAME
from database.backbone.cohorts import Cohort, Customer


class TestUserManagement(InstantCensusTestCase):

    def test_add_user_attribute(self):
        new_attribute_name = " NEW CusToM AttRIBUTE NAME     "
        saved_in_database = new_attribute_name.lower().strip()
        attributes = self.test_cohort.get_custom_attributes()
        self.assertTrue(saved_in_database not in attributes, "new attribute already exists")
        resp = self.test_app.post("/create_user_attribute", data={"new_attribute": new_attribute_name,
                                                             "default_value": "default_value",
                                                             "cohort_id": str(self.test_cohort[ID_KEY])})
        self.assertResponseOkay(resp, "create new user attribute failed")
        self.test_cohort = Cohort.get_test_cohort()
        attributes = self.test_cohort.get_custom_attributes()
        self.assertTrue(saved_in_database in attributes, "new attribute was not created")

    def test_upload_user_spreadsheet_actions(self):
        # Valid data upload succeeds
        cohort = Cohort.get_test_cohort()
        first_user_count = cohort.get_total_user_count()
        valid_upload_file = StringIO("phone number\r\n888-555-5555\r\n(888)555-5556\r\n")
        setattr(valid_upload_file, "filename", "mock_filename.csv")
        parse_uploaded_user_file(valid_upload_file, cohort, option="safe", delay=False)
        second_user_count = cohort.get_total_user_count()
        self.assertEqual(first_user_count, second_user_count - 2, "Upload of valid spreadsheet did not correctly create users")
        # remove uploaded users for other tests
        User.retrieve(phonenum="+18885555555", cohort_id=cohort[ID_KEY]).remove()
        User.retrieve(phonenum="+18885555556", cohort_id=cohort[ID_KEY]).remove()

        #############################################
        # Invalid data upload fails
        first_user_count = cohort.get_total_user_count()
        invalid_upload_file = StringIO("phone number\r\n+855+55\r\n11231313555556\r\n")
        setattr(invalid_upload_file, "filename", "mock_filename.csv")
        parse_uploaded_user_file(invalid_upload_file, cohort, option="safe", delay=False)
        second_user_count = cohort.get_total_user_count()
        self.assertEqual(first_user_count, second_user_count, "Upload of incorrect spreadsheet created users")

        #############################################
        # Unrestricted upload allows editing existing users
        first_user_count = cohort.get_total_user_count()
        # create attribute
        valid_upload_file = StringIO("phone number,NEW_HEADER\r\n888-555-5555,NEW_VALUE\r\n")
        setattr(valid_upload_file, "filename", "mock_filename.csv")
        parse_uploaded_user_file(valid_upload_file, cohort, option="unrestricted", delay=False)
        cohort = Cohort.get_test_cohort()
        second_user_count = cohort.get_total_user_count()
        self.assertEqual(first_user_count, second_user_count - 1,
                         "Upload of valid spreadsheet did not correctly create users")
        # note that custom attributes are stored lowercase
        self.assertTrue("new_header" in cohort["custom_attributes"], "New attribute not created in unrestricted upload")
        user = User.retrieve(phonenum="+18885555555", cohort_id=cohort[ID_KEY])
        self.assertTrue("new_header" in user["custom_attributes"], "New attribute not created in unrestricted upload")
        self.assertTrue("NEW_VALUE" == user["custom_attributes"]["new_header"],
                        "attribute not assigned to user in upload")
        # edit attribute value
        valid_upload_file = StringIO("phone number,NEW_HEADER\r\n888-555-5555,SECOND_NEW_VALUE\r\n")
        setattr(valid_upload_file, "filename", "mock_filename.csv")
        parse_uploaded_user_file(valid_upload_file, cohort, option="unrestricted", delay=False)
        user = User.retrieve(phonenum="+18885555555", cohort_id=cohort[ID_KEY])
        self.assertTrue("SECOND_NEW_VALUE" == user["custom_attributes"]["new_header"],
                        "user attribute not edited in unrestricted upload")

        #############################################
        # Safe upload does not allow editing existing users
        first_user_count = cohort.get_total_user_count()
        valid_upload_file = StringIO("phone number,NEW_HEADER\r\n888-555-5555,THIRD_NEW_VALUE\r\n")
        setattr(valid_upload_file, "filename", "mock_filename.csv")
        parse_uploaded_user_file(valid_upload_file, cohort, option="safe", delay=False)
        second_user_count = cohort.get_total_user_count()
        self.assertEqual(first_user_count, second_user_count,
                         "Upload of spreadsheet created users when it shouldn't have")
        user = User.retrieve(phonenum="+18885555555", cohort_id=cohort[ID_KEY])
        self.assertTrue("SECOND_NEW_VALUE" == user["custom_attributes"]["new_header"],
                        "user attribute was edited in safe upload")

        #############################################
        # Unrestricted upload allows uploading headers with weird format
        # create attribute
        header_candidate = " weirdly fORmatted hEader   "
        valid_upload_file = StringIO("phone number,%s\r\n888-555-5555,NEW_VALUE\r\n" % header_candidate)
        setattr(valid_upload_file, "filename", "mock_filename.csv")
        parse_uploaded_user_file(valid_upload_file, cohort, option="unrestricted", delay=False)
        cohort = Cohort.get_test_cohort()
        self.assertTrue(header_candidate.lower().strip() in cohort["custom_attributes"], "New attribute not created in unrestricted upload")

