from __future__ import division
from utils.database import DatabaseObject, DatabaseCollection, ID_KEY, REQUIRED
from utils.time import total_seconds, now, timedelta
from utils.codes import random_hex
from mongolia.constants import REQUIRED_STRING
from constants.exceptions import BadPasswordException


class ResponseTime(DatabaseObject):
    PATH = "analytics.response_time"
    DEFAULTS = {"user_id": REQUIRED, "question_id": REQUIRED,
                    "response_time": REQUIRED, "store_date": REQUIRED,
                    "cohort_id": REQUIRED}
    
    @classmethod
    def store(cls, user, answer_message, question):
        store_date = now()
        td = answer_message["time"] - user.last_polled_time(question[ID_KEY])
        response_time = total_seconds(td)
        return ResponseTime.create(
            {"user_id": user[ID_KEY], "question_id": question[ID_KEY],
             "response_time": response_time, "store_date": store_date,
             "cohort_id": user["cohort_id"]},
            random_id=True
        )

class ResponseTimes(DatabaseCollection):
    OBJTYPE = ResponseTime


class CronTime(DatabaseObject):
    PATH = "analytics.cron_time"
    DEFAULTS = {"cron_type": REQUIRED, "total_time": REQUIRED,
                "start_time": REQUIRED, "iterations": None}
    
    @classmethod
    def store(cls, cron_type, total_time, start_time, iterations=None):
        return super(CronTime, cls).create(
            {"cron_type": cron_type, "total_time": total_time,
             "start_time": start_time, "iterations": iterations},
            random_id=True
        )

class CronTimes(DatabaseCollection):
    OBJTYPE = CronTime


class StatusCount(DatabaseObject):
    PATH = "analytics.status_counts"
    DEFAULTS = {"status": REQUIRED, "count": REQUIRED, "cohort_id": REQUIRED, "date": REQUIRED}
    
    @classmethod
    def store(cls, status, count, cohort_id, date):
        return cls.create({"status": status, "count": count, "date": date,
                           "cohort_id": cohort_id}, random_id=True)

class StatusCounts(DatabaseCollection):
    OBJTYPE = StatusCount


class EveryHourOTP(DatabaseObject):
    PATH = "analytics.every_hour_otp"
    DEFAULTS = {"password": REQUIRED_STRING, "expiry": REQUIRED, "valid": False}
    __SINGLE_INSTANCE_ID = 0
    __MINUTES_TILL_EXPIRY = 10
    
    @classmethod
    def generate_password(cls):
        password = random_hex()
        expiry = now() + timedelta(minutes=cls.__MINUTES_TILL_EXPIRY)
        cls.create({ID_KEY: cls.__SINGLE_INSTANCE_ID, "password": password,
                    "expiry": expiry, "valid": True}, overwrite=True)
        return password
    
    @classmethod
    def check_password(cls, password):
        current_password = cls(cls.__SINGLE_INSTANCE_ID)
        if not current_password:
            raise BadPasswordException("No current password object")
        if not current_password["valid"]:
            raise BadPasswordException("Current password is not valid")
        if current_password["password"] != password:
            raise BadPasswordException("Current password does not match argument")
        if now() > current_password["expiry"]:
            raise BadPasswordException("Current password is expired")
        current_password.update(valid=False)
