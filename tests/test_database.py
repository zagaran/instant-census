from supertools.subclass_detector import all_children
from utils.database import DatabaseObject, DatabaseCollection
from database.analytics.system_load import EveryHourOTP
from constants.exceptions import BadPasswordException
from tests.common import InstantCensusTestCase


class TestDatabase(InstantCensusTestCase):
    def specials(self, cls):
        """ returns all attrs on a class in ALL_CAPS """
        return set(attr for attr in dir(cls) if attr.upper() == attr)
    
    def test_database_objects(self):
        for Subclass in all_children(DatabaseObject):
            self.assertTrue(isinstance(Subclass.PATH, str),
                             "PATH is not string for DD " + str(Subclass))
            self.assertTrue(isinstance(Subclass.DEFAULTS, dict),
                             "DEFAULTS is not dict for DD " + str(Subclass))
            self.assertEqual(self.specials(Subclass) - self.specials(dict),
                             set(['PATH', 'DEFAULTS']),
                             "extra ALL_CAPS_ATTRS on DO " + str(Subclass))
    
    def test_database_collections(self):
        database_dicts = all_children(DatabaseObject)
        for Subclass in all_children(DatabaseCollection):
            self.assertEqual(type(Subclass.OBJTYPE), type,
                             "OBJTYPE is not class for DC " + str(Subclass))
            self.assertTrue(Subclass.OBJTYPE in database_dicts,
                            "OBJTYPE is not DD subclass for DC " + str(Subclass))
            self.assertEqual(self.specials(Subclass) - self.specials(list),
                             set(['PATH', 'OBJTYPE']),
                             "extra ALL_CAPS_ATTRS on DC " + str(Subclass))
    
    def test_every_hour_otp(self):
        password = EveryHourOTP.generate_password()
        # Wrong password; should raise exception
        self.assertRaisedException(
            EveryHourOTP.check_password, BadPasswordException,
            "EveryHourOTP.check_password failed to raise exception",
            "asdfasdf"
        )
        # Good password; should work fine
        EveryHourOTP.check_password(password)
        # Password already used; should raise exception
        self.assertRaisedException(
            EveryHourOTP.check_password, BadPasswordException,
            "EveryHourOTP.check_password failed to raise exception",
            password
        )
        password = EveryHourOTP.generate_password()
        # Good password; should work fine
        EveryHourOTP.check_password(password)
