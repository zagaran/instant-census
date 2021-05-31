from database.backbone.cohorts import Cohort
from database.tracking.users import Users
from utils.database import DatabaseObject, ID_KEY, DatabaseCollection
from utils.time import now
from utils.codes import generate_access_code, code_expiration

# TODO: could be a fun project for an intern to improve this algorithm
def generate_unique_code():
    code = generate_access_code()
    while AccessCode.exists(code):
        code = generate_access_code()
    return code

# generates a code (ie, XD4SL) and allows you to point
# it to a Cohort (ie BlueCross Insurance Group)
# a User then points to an AccessCode
# can also give it an expiration time for being used
class AccessCode(DatabaseObject):
    PATH = "tracking.access_codes"
    
    DEFAULTS = {"create_time": now,
                    "expiration_time": code_expiration,
                    "cohort_id": None,
                    "user": None
                    }
    
    @staticmethod
    def retrieve(access_code):
        if AccessCode.exists(access_code): return AccessCode(access_code)
        return None
    
    def valid(self, ic_number):
        return (self["user"] is None and self["expiration_time"] > now() and
                (ic_number is None or ic_number in self.get_cohort()["ic_numbers"]))
    
    def get_cohort(self):
        if Cohort.exists(self["cohort_id"]):
            return Cohort(self["cohort_id"])
        return None
    
    def get_user(self):
        user = Users(query={"access_code": self[ID_KEY]})
        if user != []:
            return user[0] # could be more elegant
        return None
    
    def is_expired(self):
        return not self["expiration_time"] > now()
    
    def is_used(self):
        return not self.get_user() is None
    
    def is_usable(self):
        return not (self.is_used() or self.is_expired())

class AccessCodes(DatabaseCollection):
    OBJTYPE = AccessCode
