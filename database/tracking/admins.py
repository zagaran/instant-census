from constants.database import TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD, INTERNAL_SUPER_ADMIN_EMAIL
from database.backbone.cohorts import Customer
from mongolia.constants import REQUIRED_STRING, REQUIRED, ID_KEY,\
    REQUIRED_DATETIME

from constants.users import (AdminTypes, AdminStatus)
from utils.database import DatabaseObject, DatabaseCollection
from utils.time import now
import bcrypt
from utils.codes import random_string
from mongolia.errors import DatabaseConflictError


class Admin(DatabaseObject):
    PATH = "tracking.admins"

    DEFAULTS = {
        "create_time": now,
        "customer_id": REQUIRED,
        "email": REQUIRED_STRING,
        "hashed_password": None,  # so that we can make admins with None hashed_password
        "last_login_time": None,  # store to invalidate lost password requests if login has occurred since
        "last_reset_password_request_time": None,  # so that emails can't be spammed by lost password requests
        "last_reset_password_token": None,  # so that only the most recent forgot password token can be used
        "status": REQUIRED_STRING,
        "timezone": "US/Eastern",
        "type": REQUIRED_STRING,
        "signed_tos_timestamp": None,  # timestamp when admin has agreed to terms of services, otherwise None
    }

    @classmethod
    def make_admin(cls, email, password, customer_id, admin_type=AdminTypes.standard,
               status=AdminStatus.active, timezone="US/Eastern"):
        new_admin = {
            "type": admin_type,
            "customer_id": customer_id,
            "hashed_password": "",
            "status": status,
            "email": email.lower(),
            "timezone": timezone
        }
        admin = cls.create(new_admin, random_id=True)
        admin.set_password(password)
        return admin

    @staticmethod
    def get_admin(email, password):
        # TODO: verify customer id valid
        if Admin.exists(email=email):
            admin = Admin(email=email)
            hashed_password = admin["hashed_password"]
            if hashed_password and bcrypt.hashpw(str(password), str(hashed_password)) == hashed_password:
                return admin
        return None

    @staticmethod
    def get_test_admin():
        admin = Admin(email=TEST_ADMIN_EMAIL)
        if not admin:
            admin = Admin.make_admin(TEST_ADMIN_EMAIL, TEST_ADMIN_PASSWORD, Customer.get_internal_customer()[ID_KEY])
        admin.update({"signed_tos_timestamp": now()})
        return admin

    @staticmethod
    def get_internal_super_admin():
        super_admin = Admin(email=INTERNAL_SUPER_ADMIN_EMAIL)
        if not super_admin:
            print ("\n\n" +
                   "************************************\n" +
                   "************* WARNING! *************\n" +
                   "************************************\n" +
                   "super_admin newly created; please manually set super_admin customer_id to match the " +
                   "customer on this deployment\n\n" +
                   "command: super_admin.update({customer_id: ObjectId('xxxxxxxxxxxxxxxxxxxxxxxx')})\n\n")
            super_admin = Admin.make_admin(INTERNAL_SUPER_ADMIN_EMAIL, None, Customer.get_internal_customer()[ID_KEY])
            super_admin.update({"hashed_password": None, "type": AdminTypes.super})
        return super_admin

    def set_password(self, password):
        hashed_password = bcrypt.hashpw(str(password), bcrypt.gensalt())
        self.update({"hashed_password": hashed_password})


class Admins(DatabaseCollection):
    OBJTYPE = Admin


class AdminAction(DatabaseObject):
    PATH = "tracking.admin_action"
    DEFAULTS = {
        "admin_id": REQUIRED,
        "path": REQUIRED_STRING,
        "url": REQUIRED_STRING,
        "get_params": {},
        "post_params": {},
        "timestamp": now
    }
    
    @classmethod
    def log_action(cls, admin_id, path, url, get_params={}, post_params={}):
        cls.create({
            "admin_id": admin_id,
            "path": path,
            "url": url,
            "get_params": get_params,
            "post_params": post_params
        }, random_id=True)

class AdminActions(DatabaseCollection):
    OBJTYPE = AdminAction


class APICredential(DatabaseObject):
    PATH = "tracking.api_credential"
    DEFAULTS = {
        "admin_id": REQUIRED,
        "key": REQUIRED_STRING,
        "secret": REQUIRED_STRING,
        "expiration": REQUIRED_DATETIME,
    }
    
    @classmethod
    def make_credential(cls, admin, expiration):
        for _ in range(100):
            key = random_string(20)
            if not cls.exists(key=key):
                break
        else:
            raise DatabaseConflictError("Could not generate available key")
        secret = random_string(40)
        data = {"key": key, "secret": secret,
                "admin_id": admin[ID_KEY], "expiration": expiration}
        return cls.create(data, random_id=True)

class APICredentials(DatabaseCollection):
    OBJTYPE = APICredential
