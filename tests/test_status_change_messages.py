from app import app
from backend.incoming.new_user import onboard_user
from constants.cohorts import CohortStatus
from constants.messages import (DEFAULT_USER_PAUSE, DEFAULT_USER_RESTART,
    DEFAULT_COHORT_PAUSE, DEFAULT_COHORT_RESTART, DEFAULT_WELCOME)
from constants.database import TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD
from database.tracking.admins import Admin
from database.tracking.messages import ControlMessage
from database.tracking.users import User, Status
from utils.database import ID_KEY
from tests.common import InstantCensusTestCase
from database.backbone.cohorts import Cohort, Customer
from utils.time import now


##############################################################################################################
########################################## ADMIN STATUS ACTION TESTS #########################################
##############################################################################################################

class TestStatusChangeMessages(InstantCensusTestCase):
    
    def setUp(self):
        self.set_test_items()
        onboard_user(self.test_user, now(), delay=False)
    
    def test_if_admin_activates_user(self):
        """
        If Admin Activates User when:
        Cohort is Active:  msg sent: DEFAULT_USER_RESTART; cohort status: CohortStatus.active; user status: Status.active
        Cohort is Paused:  msg sent: None; cohort status: CohortStatus.paused ; user status: Status.active
        """
        
        PARAMETERS = {
            # conditions:
            "test_cohort_initial_status": CohortStatus.active,
            "test_user_initial_status": Status.paused,
            "test_user_onboarded": True,
            # expect:
            "expected_cohort_status": CohortStatus.active,
            "expected_user_status": Status.active,
            "expected_send_message": DEFAULT_USER_RESTART
        }
        URL = "/set_user_attribute"
        DATA = {
            "attribute_name": "status",
            "new_value": Status.active,
            "user_id": self.test_user[ID_KEY]
        }
        self.do_post_actions_and_checks(URL, DATA, PARAMETERS)
        
        PARAMETERS = {
            # conditions:
            "test_cohort_initial_status": CohortStatus.paused,
            "test_user_initial_status": Status.paused,
            "test_user_onboarded": True,
            # expect:
            "expected_cohort_status": CohortStatus.paused,
            "expected_user_status": Status.active,
            "expected_send_message": None
        }
        URL = "/set_user_attribute"
        DATA = {
            "attribute_name": "status",
            "new_value": Status.active,
            "user_id": self.test_user[ID_KEY]
        }
        self.do_post_actions_and_checks(URL, DATA, PARAMETERS)
    
    def test_if_admin_pauses_user(self):
        """
        If Admin Pauses User when:
        Cohort is Active:  msg sent: DEFAULT_USER_PAUSE; cohort status: CohortStatus.active; user status: Status.paused
        Cohort is Paused:  msg sent: None; cohort status: CohortStatus.paused; user status: Status.paused
        """
        
        PARAMETERS = {
            # conditions:
            "test_cohort_initial_status": CohortStatus.active,
            "test_user_initial_status": Status.active,
            "test_user_onboarded": True,
            # expect:
            "expected_cohort_status": CohortStatus.active,
            "expected_user_status": Status.paused,
            "expected_send_message": DEFAULT_USER_PAUSE
        }
        URL = "/set_user_attribute"
        DATA = {
            "attribute_name": "status",
            "new_value": Status.paused,
            "user_id": self.test_user[ID_KEY]
        }
        self.do_post_actions_and_checks(URL, DATA, PARAMETERS)
        
        PARAMETERS = {
            # conditions:
            "test_cohort_initial_status": CohortStatus.paused,
            "test_user_initial_status": Status.active,
            "test_user_onboarded": True,
            # expect:
            "expected_cohort_status": CohortStatus.paused,
            "expected_user_status": Status.paused,
            "expected_send_message": None
        }
        URL = "/set_user_attribute"
        DATA = {
            "attribute_name": "status",
            "new_value": Status.paused,
            "user_id": self.test_user[ID_KEY]
        }
        self.do_post_actions_and_checks(URL, DATA, PARAMETERS)
    
    def test_if_admin_activates_cohort(self):
        """
        If Admin Activates Cohort when:
        User is Active:  msg sent: DEFAULT_COHORT_RESTART; cohort status: CohortStatus.active; user status: Status.active
        User is Paused:  msg sent: None; cohort status: CohortStatus.active; user status: Status.paused
        """
        # before user onboarded
        PARAMETERS = {
            # conditions:
            "test_cohort_initial_status": CohortStatus.paused,
            "test_user_initial_status": Status.active,
            "test_user_onboarded": False,
            # expect:
            "expected_cohort_status": CohortStatus.active,
            "expected_user_status": Status.active,
            "expected_send_message": DEFAULT_WELCOME  # user hasn't been onboarded yet
        }
        URL = "/change_cohort_status"
        DATA = {
            "cohort_id": self.test_cohort[ID_KEY],
            "new_value": CohortStatus.active
        }
        self.do_post_actions_and_checks(URL, DATA, PARAMETERS)
        # after user onboarded
        PARAMETERS["test_user_onboarded"] = True
        PARAMETERS["expected_send_message"] = DEFAULT_COHORT_RESTART  # user has been onboarded
        self.do_post_actions_and_checks(URL, DATA, PARAMETERS)

        PARAMETERS = {
            # conditions:
            "test_cohort_initial_status": CohortStatus.paused,
            "test_user_initial_status": Status.paused,
            "test_user_onboarded": True,
            # expect:
            "expected_cohort_status": CohortStatus.active,
            "expected_user_status": Status.paused,
            "expected_send_message": None
        }
        URL = "/change_cohort_status"
        DATA = {
            "cohort_id": self.test_cohort[ID_KEY],
            "new_value": CohortStatus.active
        }
        self.do_post_actions_and_checks(URL, DATA, PARAMETERS)
    
    def test_if_admin_pauses_cohort(self):
        """
        If Admin Pauses Cohort when:
        User is Active:  msg sent: DEFAULT_COHORT_PAUSE; cohort status: CohortStatus.paused; user status: Status.active
        User is Paused:  msg sent: None; cohort status: CohortStatus.paused; user status: Status.paused
        """
                
        PARAMETERS = {
            # conditions:
            "test_cohort_initial_status": CohortStatus.active,
            "test_user_initial_status": Status.active,
            "test_user_onboarded": True,
            # expect:
            "expected_cohort_status": CohortStatus.paused,
            "expected_user_status": Status.active,
            "expected_send_message": DEFAULT_COHORT_PAUSE
        }
        URL = "/change_cohort_status"
        DATA = {
            "cohort_id": self.test_cohort[ID_KEY],
            "new_value": CohortStatus.paused
        }
        self.do_post_actions_and_checks(URL, DATA, PARAMETERS)
        
        PARAMETERS = {
            # conditions:
            "test_cohort_initial_status": CohortStatus.active,
            "test_user_initial_status": Status.paused,
            "test_user_onboarded": True,
            # expect:
            "expected_cohort_status": CohortStatus.paused,
            "expected_user_status": Status.paused,
            "expected_send_message": None
        }
        URL = "/change_cohort_status"
        DATA = {
            "cohort_id": self.test_cohort[ID_KEY],
            "new_value": CohortStatus.paused
        }
        # self
        self.do_post_actions_and_checks(URL, DATA, PARAMETERS)
    
    ##############################################################################################################
    ########################################## USER STATUS ACTION TESTS ##########################################
    ##############################################################################################################
    
    def test_if_user_texts_start(self):
        """
        If User Texts 'START' when:
        Cohort is Active:
            User Active: msg sent: none user status: Status.active
            User Disabled: msg sent: DEFAULT_USER_RESTART user status: Status.active
            User Inactive: msg sent: DEFAULT_USER_RESTART user status: Status.active
            User Paused: msg sent: none user status: Status.active
        Cohort is Paused:
            User Active: msg sent: none user status: Status.active
            User Disabled: msg sent: DEFAULT_PAUSED_COHORT_USER_RESTART user status: Status.active
            User Inactive: msg sent: DEFAULT_PAUSED_COHORT_USER_RESTART user status: Status.active
            User Paused: msg sent: none user status: Status.active
        """
        pass
    
    def test_if_user_texts_stop(self):
        """
        If User Texts 'STOP' when:
        Cohort is Active:
            User Active: msg sent: TWILIO stop user status: Status.disabled
            User Disabled: msg sent: TWILIO stop user status: Status.disabled
            User Inactive: msg sent: TWILIO stop user status: Status.disabled
            User Paused: msg sent: TWILIO stop user status: Status.disabled
        Cohort is Paused:
            User Active: msg sent: TWILIO stop user status: Status.disabled
            User Disabled: msg sent: TWILIO stop user status: Status.disabled
            User Inactive: msg sent: TWILIO stop user status: Status.disabled
            User Paused: msg sent: TWILIO stop user status: Status.disabled
        """
        pass
    
    def test_if_user_texts_something(self):
        """
        If User Texts 'STOP' when:
        Cohort is Active:
            User Active: msg sent: None user status: Status.active
            User Disabled: msg sent: None user status: Status.disabled
            User Inactive: msg sent: DEFAULT_USER_RESTART user status: Status.active
            User Paused: msg sent: None user status: Status.paused
        Cohort is Paused:
            User Active: msg sent: None user status: Status.active
            User Disabled: msg sent: DEFAULT_PAUSED_COHORT_USER_RESTART user status: Status.active
            User Inactive: msg sent: DEFAULT_PAUSED_COHORT_USER_RESTART user status: Status.active
            User Paused: msg sent: None user status: Status.paused
        """
        pass
    
    ##############################################################################################################
    ############################################# HELPER FUNCTIONS  ##############################################
    ##############################################################################################################
    
    def do_post_actions_and_checks(self, url, data, parameters):
        # get pre-action values
        test_cohort_before = Cohort.get_test_cohort(False)
        test_user_before = User.get_test_user()
        message_before = ControlMessage.last_sent(test_user_before[ID_KEY])
        text_before = message_before["text"]
        id_before = message_before["twilio_message_sid"]
        # set initial conditions
        test_cohort_before.set_status(parameters["test_cohort_initial_status"])
        test_user_before.set_status(parameters["test_user_initial_status"])
        test_user_before.update(onboarded=parameters["test_user_onboarded"])
        # do action
        response = self.test_app.post(url, data=data)
        self.assertResponseOkay(response, "Bad return status on /set-user_attribute")
        # get post-action value
        test_cohort_after = Cohort.get_test_cohort(activate=False)
        test_user_after = User.get_test_user()
        message_after = ControlMessage.last_sent(test_user_after[ID_KEY])
        text_after = message_after["text"]
        id_after = message_after["twilio_message_sid"]
        # assertions
        if "expected_cohort_status" in parameters and parameters["expected_cohort_status"]:  # expected cohort status
            self.assertEqual(
                test_cohort_after["status"],
                parameters["expected_cohort_status"],
                "Cohort status not as expected. New: (%s), Expected: (%s)" % \
                    (test_cohort_after["status"], parameters["expected_cohort_status"])
            )
        if "expected_user_status" in parameters and parameters["expected_user_status"]:  # expected user status
            self.assertEqual(
                test_user_after["status"],
                parameters["expected_user_status"],
                "User status not as expected. New: (%s), Expected: (%s)" % \
                    (test_user_after["status"], parameters["expected_user_status"])
            )
        if "expected_send_message" in parameters:
            if parameters["expected_send_message"]:  # expected send message
                self.assertEqual(
                    text_after,
                    parameters["expected_send_message"],
                    "Message not as expected. Received: (%s), Expected: (%s)" % \
                        (text_after, parameters["expected_send_message"])
                )
            elif parameters["expected_send_message"] is None:  # not expecting send message
                self.assertEqual(
                    id_before,
                    id_after,
                    "Message received, but was not expected: (%s)" % (text_after)
                )
        # return
        return {
            "message_before": message_before,
            "id_before": id_before,
            "text_before": text_before,
            "test_cohort_before": test_cohort_before,
            "test_user_before": test_user_before,
            "message_after": message_after,
            "id_after": id_after,
            "text_after": text_after,
            "test_cohort_after": test_cohort_after,
            "test_user_after": test_user_after,
            "response": response
        }
