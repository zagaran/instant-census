from bson import ObjectId
from constants.users import ALL_ADMIN_TYPES, AdminStatus
from database.backbone.cohorts import Customer
from database.tracking.admins import Admin, AdminAction, APICredential
from mongolia import ID_KEY
from utils.time import now, timedelta
from flask import session, redirect, request, abort, flash
import functools


SESSION_VARIABLES = [
    "admin_id",
    "admin_email",
    "admin_type",
    "customer_id",
    "customer_name",
    "expiry"
]


def is_logged_in(admin_types=ALL_ADMIN_TYPES):
    # if all session variables exist in session list
    if all([True if s in session else False for s in SESSION_VARIABLES]):
        # if session has expired, delete and return False
        if session["expiry"] < now():
            del_loggedin_admin()
            return False
        # check if admin user is real and is of type we want
        if is_admin_type(admin_types):
            # add one minute to expiry to prevent simulator from logging you out
            session["expiry"] = now() + timedelta(days=1, minutes=1)
            return True
    del_loggedin_admin()
    return False

def is_admin_type(admin_types):
    if session and "admin_id" in session:
        admin = Admin(ObjectId(session["admin_id"]))
        if admin and admin["type"] in admin_types:
            return True
    return False


def del_loggedin_admin():
    for variable in SESSION_VARIABLES:
        if variable in session:
            del session[variable]


def set_loggedin_admin(admin):
    """ logs in customer attached to cohort that contains the admin """
    session["admin_id"] = str(admin[ID_KEY])
    session["admin_email"] = str(admin["email"])
    session["admin_type"] = admin["type"]
    session["customer_id"] = str(admin["customer_id"])
    session["customer_name"] = Customer(admin["customer_id"])["customer_name"]
    session["expiry"] = now() + timedelta(hours=5)
    session["tos"] = False
    if admin["signed_tos_timestamp"]:
        session["tos"] = True


def admin(f):
    """ auth decorator """
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if is_logged_in():
            # if hasn't signed tos, redirect to tos
            if "tos" not in session or not session["tos"]:
                flash("Welcome to Instant Census. You must read and agree to the terms of service before continuing.")
                return redirect("/tos")
            AdminAction.log_action(session["admin_id"], request.path, request.url,
                                   dict(request.args), dict(request.form))
            return f(*args, **kwargs)
        return redirect("/")
    return wrapped


def api(f):
    """ api decorator """
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        key = request.args["key"]
        secret = request.args["secret"]
        api_credential = APICredential(key=key)
        if not api_credential or api_credential["secret"] != secret:
            abort(403)
        if api_credential["expiration"] < now():
            abort(403)
        admin = Admin(api_credential["admin_id"])
        if not admin or admin["status"] != AdminStatus.active:
            abort(403)
        AdminAction.log_action(admin[ID_KEY], request.path, request.url,
                               dict(request.args), dict(request.form))
        return f(*args, **kwargs)
    return wrapped
