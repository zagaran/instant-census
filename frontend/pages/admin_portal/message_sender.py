from flask import request, session, jsonify, flash
from flask.blueprints import Blueprint
from pytz import UnknownTimeZoneError
import pytz

from bson.objectid import ObjectId

from backend.admin_portal.common_helpers import validate_cohort, validate_user, validate_cohort_id_match, \
    raise_404_error, raise_400_error
from backend.admin_portal.survey_builder_helpers import check_attributes
from backend.outgoing.exit_points import send_control_message
from conf.settings import SHOW_DELETED_USERS
from constants.cohorts import CohortStatus
from constants.messages import DEFAULT_USER_PAUSE, DEFAULT_USER_RESTART
from constants.users import Status
from database.tracking.admins import Admin
from frontend import templating, auth
from utils.formatters import convert_unicode
from utils.time import convert_from_utc, now


message_sender = Blueprint('message_sender', __name__)


@message_sender.route("/<cohort_id>/send/<user_id>", methods=["GET"])
@auth.admin
@templating.template("/admin_portal/message_sender.html")
def render_message_sender(cohort_id, user_id):
    user = validate_user(user_id)
    admin = Admin(ObjectId(session["admin_id"]))
    # do not show if deleted and option isn't set
    if not SHOW_DELETED_USERS and user["status"] == Status.deleted:
        raise_404_error("User not found.")
    cohort = validate_cohort(cohort_id)
    if cohort["status"] == CohortStatus.completed:
        cohort_completed = True
    else:
        cohort_completed = False
    validate_cohort_id_match(user["cohort_id"], ObjectId(cohort_id))
    # get data
    user_messages = user.all_messages()
    # convert messages to admin timezone
    admin_timezone = admin["timezone"]
    for message in user_messages:
        try:
            message["time"] = convert_from_utc(message["time"], admin_timezone)
        except UnknownTimeZoneError:
            pass
    # convert user create time to admin timezone and set 3 letter timezone
    timezone = ""
    try:
        user["create_time"] = convert_from_utc(user["create_time"], admin_timezone)
        timezone = pytz.timezone(admin_timezone).tzname(now(), is_dst=False)
    except UnknownTimeZoneError:
        pass
    return {
        "page": "message_sender",
        "cohort": cohort,
        "cohort_id": cohort_id,
        "COHORT_COMPLETED": cohort_completed,
        "timezone": timezone,
        "user": user,
        "user_messages": user_messages,
        "DEFAULT_COHORT_PAUSE": DEFAULT_USER_PAUSE,
        "DEFAULT_USER_RESTART": DEFAULT_USER_RESTART
    }


@message_sender.route("/send_manual_message", methods=["POST"])
@auth.admin
def send_manual_message():
    user_id = request.form["user_id"]
    user = validate_user(user_id)
    # do not send if user is deleted
    if user["status"] == Status.deleted:
        raise_400_error("User is deleted.")
    cohort_id = request.form["cohort_id"]
    cohort = validate_cohort(cohort_id)
    validate_cohort_id_match(user["cohort_id"], ObjectId(cohort_id))
    if cohort.is_initiated() == False:
        flash("This action is not allowed on a cohort that has not been initiated or has been completed.", "error")
        return jsonify({
            "reload": "true"
        })
    message = convert_unicode(request.form["message"])
    try:
        check_attributes({"text": message}, cohort)
    except:
        # The flash message happens in check_attributes, but we run a try/except to force frontend to reload
        return jsonify({
            "reload": "true"
        })
    send_control_message(user, message, delay=False)
    return "success"


@message_sender.route("/mark_as_handled", methods=["POST"])
@auth.admin
def mark_as_handled():
    user_id = request.form["userId"]
    user = validate_user(user_id)
    # mark user messages as handled
    user_messages = user.all_messages()
    for message in user_messages:
        if "needs_review" in message and message["needs_review"] is True:
            message.update(needs_review=False)
    # mark user as handled
    user.update(needs_review=False)
    return "success"