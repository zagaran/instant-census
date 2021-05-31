
from bson import ObjectId

from flask import Blueprint, flash, request, redirect, session
from mongolia.constants import ID_KEY
from pytz import UnknownTimeZoneError
import pytz

from backend.admin_portal.cohorts_dashboard_helpers import retrieve_cohorts_by_admin, \
    add_cohort_info
from backend.admin_portal.common_helpers import (validate_cohort, check_cohort_name,
    check_inactive_limit, check_area_code, raise_400_error)
from backend.admin_portal.survey_builder_helpers import check_attributes
from backend.incoming.new_user import onboard_user
from backend.outgoing.dispatcher import send_cohort_reactivation_message, send_cohort_pause_message
from conf.settings import (CUSTOM_WELCOME_OVERRIDE, DISABLE_WELCOME, DISABLE_LENGTH_RESTRICTION, ADMIN_LEVEL_VISIBILITY,
    DISABLE_COHORT_STATUS_CHANGE_MESSAGES, COHORTS_LIMIT)
from conf.settings import SHOW_DELETED_USERS
from constants.cohorts import COHORT_STATUSES, CohortStatus
from constants.messages import (LEGALLY_REQUIRED, DEFAULT_COHORT_PAUSE, DEFAULT_COHORT_RESTART,
                                DEFAULT_WELCOME_CUSTOMIZABLE)
from constants.users import AdminTypes
from database.backbone.cohorts import Cohorts, Cohort, Customer
from database.tracking.admins import Admin
from database.tracking.messages import Messages
from database.tracking.users import Users
from frontend import templating, auth
from frontend.auth import is_admin_type
from utils.formatters import phone_humanize, convert_unicode, encode_unicode
from utils.server import PRODUCTION
from utils.time import convert_from_utc, now
from utils.twilio_utils import release_phonenumbers


cohorts_dashboard = Blueprint('cohorts_dashboard', __name__)


@cohorts_dashboard.app_template_filter()
def phonenum_humanize_filter(phone_num_or_list):
    """ Humanizes a phone number or list of phone numbers"""
    if not phone_num_or_list:
        return ""
    if isinstance(phone_num_or_list, list):
        return ", ".join([phone_humanize(pn) for pn in phone_num_or_list])
    else:
        return phone_humanize(phone_num_or_list)


@cohorts_dashboard.route("/cohorts")
@auth.admin
@templating.template('admin_portal/cohorts_dashboard.html')
def render_cohorts_dashboard():
    customer = Customer(ObjectId(session["customer_id"]))
    admin = Admin(ObjectId(session["admin_id"]))
    cohorts, all_cohorts = retrieve_cohorts_by_admin()
    # convert cohort create time to admin timezone
    admin_timezone = admin["timezone"]
    for cohort in cohorts:
        try:
            cohort["create_time"] = convert_from_utc(cohort["create_time"], admin_timezone)
        except UnknownTimeZoneError:
            pass
    # set 3 letter timezone
    timezone = ""
    try:
        timezone = pytz.timezone(admin_timezone).tzname(now(), is_dst=False)
    except UnknownTimeZoneError:
        pass
    # get other information to display
    # total_messages = customer.get_total_message_count()
    total_number_of_initiated_cohorts = len([c for c in all_cohorts if c["status"] != CohortStatus.completed])
    admin_number_of_initiated_cohorts = len([c for c in cohorts if c["status"] != CohortStatus.completed])
    # split cohorts into completed/not completed
    completed_cohorts = [add_cohort_info(c) for c in cohorts if c["status"] == CohortStatus.completed]
    non_completed_cohorts = [add_cohort_info(c) for c in cohorts if c["status"] != CohortStatus.completed]
    return {
        "completed_cohorts": completed_cohorts,
        "non_completed_cohorts": non_completed_cohorts,
        "customer": customer,
        # "messages_left": customer["message_limit"] - total_messages,
        "page": "cohorts",
        "timezone": timezone,
        # "total_messages": total_messages,
        "CUSTOM_WELCOME_OVERRIDE": CUSTOM_WELCOME_OVERRIDE,
        "DEFAULT_COHORT_PAUSE": DEFAULT_COHORT_PAUSE,
        "DEFAULT_USER_RESTART": DEFAULT_COHORT_RESTART,
        "DEFAULT_WELCOME_CUSTOMIZABLE": DEFAULT_WELCOME_CUSTOMIZABLE,
        "DISABLE_WELCOME": DISABLE_WELCOME,
        "LEGALLY_REQUIRED": LEGALLY_REQUIRED,
        "SHOW_DELETED_USERS": SHOW_DELETED_USERS,
        "DISABLE_COHORT_STATUS_CHANGE_MESSAGES": DISABLE_COHORT_STATUS_CHANGE_MESSAGES,
        "COHORTS_LIMIT": COHORTS_LIMIT,
        "total_number_of_initiated_cohorts": total_number_of_initiated_cohorts,
        "admin_number_of_initiated_cohorts": admin_number_of_initiated_cohorts,
    }


@cohorts_dashboard.route('/create_cohort', methods=["POST"])
@auth.admin
def create_cohort():
    if COHORTS_LIMIT:
        all_cohorts = Cohorts.retrieve_by_customer(ObjectId(session["customer_id"]))
        number_of_active_cohorts = len([c for c in all_cohorts if c["status"] not in [CohortStatus.completed, CohortStatus.deleted]])
        if number_of_active_cohorts >= COHORTS_LIMIT:
            flash("Sorry, the cohort was not created because the deployment's cohort limit of %s has been reached." % COHORTS_LIMIT, "error")
            return ""
    # get data
    cohort_name = check_cohort_name(request.form.get("cohort_name"))
    area_code = check_area_code(request.form.get("area_code"))
    inactive_limit = check_inactive_limit(request.form.get("inactive_limit"))
    inactive_time_limit = check_inactive_limit(request.form.get("inactive_time_limit"))
    welcome_message = convert_unicode(request.form.get("welcome_message"))
    if DISABLE_WELCOME:
        welcome_message = DEFAULT_WELCOME_CUSTOMIZABLE
    if CUSTOM_WELCOME_OVERRIDE:
        welcome_message = CUSTOM_WELCOME_OVERRIDE
    # create cohort
    new_cohort = Cohort.create(cohort_name, ObjectId(session["customer_id"]), admin_id=ObjectId(session["admin_id"]))
    # set cohort options
    new_cohort["area_code"] = area_code
    new_cohort["inactive_limit"] = inactive_limit
    new_cohort["inactive_time_limit"] = inactive_time_limit
    new_cohort["welcome_message"] = welcome_message
    new_cohort.save()
    # return
    flash("Your new cohort '%s' has been created!" % cohort_name, "success")
    return "success"


@cohorts_dashboard.route('/modify_cohort', methods=["POST"])
@auth.admin
def modify_cohort():
    # get data
    cohort = validate_cohort(request.form.get("cohort_id"))
    cohort_name = check_cohort_name(request.form.get("cohort_name"), existing_id=cohort[ID_KEY])
    area_code = check_area_code(request.form.get("area_code"))
    inactive_limit = check_inactive_limit(request.form.get("inactive_limit"))
    inactive_time_limit = check_inactive_limit(request.form.get("inactive_time_limit"))
    welcome_message = encode_unicode(convert_unicode(request.form.get("welcome_message")))
    check_attributes({"text": welcome_message}, cohort)
    # set cohort options
    cohort["cohort_name"] = cohort_name
    cohort["area_code"] = area_code
    cohort["inactive_limit"] = inactive_limit
    cohort["inactive_time_limit"] = inactive_time_limit
    if not DISABLE_WELCOME and not CUSTOM_WELCOME_OVERRIDE:
        cohort["welcome_message"] = welcome_message
    cohort.save()
    # return
    flash("Your cohort '%s' has been successfully modified." % cohort_name, "success")
    return "success"


@cohorts_dashboard.route('/delete/<cohort_id>', methods=["GET", "POST"])
@auth.admin
def delete_cohort(cohort_id):
    cohort = validate_cohort(cohort_id)
    # users = Users(cohort_id=cohort[ID_KEY])
    # questions = Questions(cohort_id=cohort[ID_KEY])
    # schedules = Schedules(cohort_id=cohort[ID_KEY])
    # #messages
    # for user in users:
    #     user.remove()
    # for question in questions:
    #     question.remove()
    # for schedule in schedules:
    #     schedule.remove()
    if PRODUCTION:
        release_phonenumbers(cohort["ic_numbers"])
    cohort.set_status(CohortStatus.deleted)
    cohort.remove_needs_review()
    flash("Your cohort '%s' has been successfully deleted." % cohort["cohort_name"], "success")
    return redirect("/cohorts")


@cohorts_dashboard.route('/complete/<cohort_id>', methods=["GET", "POST"])
@auth.admin
def complete_cohort(cohort_id):
    cohort = validate_cohort(cohort_id)
    if PRODUCTION:
        release_phonenumbers(cohort["ic_numbers"])
    cohort.set_status(CohortStatus.completed)
    cohort.remove_needs_review()
    flash("Your cohort '%s' has been successfully marked as completed." % cohort["cohort_name"], "success")
    return redirect("/cohorts")


@cohorts_dashboard.route('/change_cohort_status', methods=["POST"])
@auth.admin
def change_cohort_status():
    cohort = validate_cohort(request.form.get("cohort_id"))
    new_value = request.form.get('new_value')
    if new_value not in COHORT_STATUSES:
        raise_400_error("Invalid Cohort Status. You are attempting to change the status of a cohort to something invalid.")
    cohort.set_status(new_value)
    for user in Users(cohort_id=cohort[ID_KEY]):
        user.clear_executions()
        if not user["onboarded"]:
            if cohort["status"] == CohortStatus.active:
                onboard_user(user, now())
        elif user.is_active() and not DISABLE_COHORT_STATUS_CHANGE_MESSAGES:
            if cohort["status"] == CohortStatus.active:
                send_cohort_reactivation_message(user)
            elif cohort["status"] == CohortStatus.paused:
                send_cohort_pause_message(user)
    return "success"