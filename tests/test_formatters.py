from backend.outgoing.message_builder import merge_in_custom_attributes
from database.backbone.cohorts import Cohort
from database.tracking.users import User
from tests.common import InstantCensusTestCase
from utils.formatters import phone_format
from constants.exceptions import BadPhoneNumberError

class TestFormatters(InstantCensusTestCase):
    def test_phone_format(self):
        self.assertTrue(phone_format("(555) 555 5553") == "+15555555553", "phone_format test 1 failed")
        self.assertTrue(phone_format("(555) 555 5553") == "+15555555553", "phone_format test 2 failed")
        self.assertTrue(phone_format("(555) 555 5553") == "+15555555553", "phone_format test 3 failed")
        self.assertTrue(phone_format("5555555553") == "+15555555553", "phone_format test 4 failed")
        self.assertTrue(phone_format("+15555555553") == "+15555555553", "phone_format test 5 failed")
        self.assertTrue(phone_format("(555) ()(()()..----..555 5..---)(553") == "+15555555553", "phone_format test 6 failed")
        self.assertRaisedException(phone_format, BadPhoneNumberError, "phone_format test 7 failed", "123")
        self.assertRaisedException(phone_format, BadPhoneNumberError, "phone_format test 8 failed", "asdf123123123")
        self.assertRaisedException(phone_format, BadPhoneNumberError, "phone_format test 9 failed", "+112312+3123")

    def test_merge_fields(self):
        # setup
        cohort = Cohort.get_test_cohort()
        user = User.get_test_user()
        cohort.update({"custom_attributes": {
            "foo": "bar"
        }})
        user.update({"custom_attributes": {
           "baz": "biz"
        }})
        # tests
        message_text = "Hello, world. My [[baz]] is [[foo]]!"
        processed_text = merge_in_custom_attributes(message_text, user=user)
        self.assertEqual(processed_text, "Hello, world. My biz is bar!")
        message_text = "Hello, world. My [[boo]] is [[baa]]!"
        self.assertRaises(Exception, merge_in_custom_attributes, (message_text), user=user)