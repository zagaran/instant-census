from datetime import timedelta
import hmac

from flask import flash, json

from database.tracking.admins import Admin
from conf.secure import APP_SECRET_KEY
from utils.time import now


def check_token(token):
    admin = Admin(last_reset_password_token=str(token))
    if admin:
        current_time = now()
        last_reset = admin["last_reset_password_request_time"]
        # Password reset request expires after 4 hours
        if last_reset and (current_time - last_reset) > timedelta(hours=4):
            flash("Your password reset request has expired. Please make a new request.", "error")
            return False
        # What's stored in the database is hashed to compare against sent out token
        payload = {
            "email": admin["email"],
            "hashed_password": admin["hashed_password"],
            "last_login_time": admin["last_login_time"],
            "last_reset_password_request_time": str(last_reset)
        }
        database_token = hmac.new(APP_SECRET_KEY, json.dumps(payload)).hexdigest()
        if database_token == token:
            return True
        else:
            flash("Your password reset request has expired or is no longer valid. Please make a new request.", "error")
            return False
    flash(("Invalid password reset request. Please make a new request or contact us at " +
           "support@instantcensus.com."), "error")
    return False