from flask import Blueprint, request, flash, jsonify
import hashlib
import json
from mongolia.constants import ID_KEY
from pytz import all_timezones, os

from bson.objectid import ObjectId
from werkzeug.utils import secure_filename

from backend.admin_portal.common_helpers import validate_cohort, validate_user, raise_400_error
from backend.admin_portal.user_managment_helpers import (parse_uploaded_user_file, send_status_message,
                                                         update_merge_fields_in_object, validate_user_attribute)
from backend.incoming.new_user import new_user_via_admin_portal, onboard_user
from conf.settings import SHOW_DELETED_USERS, TIMEZONE_SUPPORT, COHORT_USER_LIMIT
from constants.cohorts import CohortStatus, FORBIDDEN_CUSTOM_ATTRIBUTES
from constants.database import EXCLUDE_DELETED_USERS_QUERY
from constants.download_data import TS_FORMAT
from constants.exceptions import BadPhoneNumberError
from constants.messages import DEFAULT_USER_PAUSE, DEFAULT_USER_RESTART
from constants.users import Status
from database.backbone.schedules import Questions, Conditionals
from database.tracking.users import User, Users
from frontend import templating, auth
from frontend.pages.admin_portal.cohorts_dashboard import phonenum_humanize_filter
from utils.formatters import phone_format, convert_unicode
from utils.server import PRODUCTION
from utils.time import now


user_management = Blueprint("user_management", __name__)

@user_management.route("/<cohort_id>/users", methods=["GET", "POST"])
@auth.admin
@templating.template("admin_portal/user_management.html")
def render_user_management(cohort_id):
    # validate cohort
    cohort = validate_cohort(cohort_id)
    users_count = Users.count(cohort_id=cohort[ID_KEY])
    if cohort["status"] == CohortStatus.completed:
        cohort_completed = True
    else:
        cohort_completed = False
    return {
            "cohort": cohort,
            "COHORT_COMPLETED": cohort_completed,
            "custom_attributes": cohort["custom_attributes"],
            "page": "users",
            "DEFAULT_COHORT_PAUSE": DEFAULT_USER_PAUSE,
            "DEFAULT_USER_RESTART": DEFAULT_USER_RESTART,
            "FORBIDDEN_CUSTOM_ATTRIBUTES": json.dumps(FORBIDDEN_CUSTOM_ATTRIBUTES),
            "TIMEZONE_SUPPORT": TIMEZONE_SUPPORT,
            "ALL_TIMEZONES": all_timezones,
            "users_count": users_count
           }


@user_management.route('/create_user_attribute', methods=["POST"])
@auth.admin
def create_user_attribute():
    # get attribute data
    new_attribute_name = convert_unicode(request.form.get("new_attribute").lower().strip())
    default_value = convert_unicode(request.form.get("default_value").strip())
    # get cohort
    cohort_id = request.form.get("cohort_id")
    cohort = validate_cohort(cohort_id)
    # error checking
    validate_user_attribute(new_attribute_name, default_value, cohort)
    # add attribute
    cohort.add_custom_attribute(new_attribute_name, default_value)
    for user in Users(cohort_id=ObjectId(cohort_id)):
        user.add_custom_attribute(new_attribute_name, default_value)
    flash("Your new custom user attribute '%s' has been successfully created." % new_attribute_name.upper(), "success")
    return "success"


@user_management.route("/edit_user_attribute", methods=["POST"])
@auth.admin
def edit_user_attribute():
    # get attribute data
    new_attribute_name = convert_unicode(request.form.get("new_attribute_name").lower().strip())
    new_default_value = convert_unicode(request.form.get("new_default_value").strip())
    previous_attribute_name = convert_unicode(request.form.get("previous_attribute_name").lower().strip())
    previous_default_value = convert_unicode(request.form.get("previous_default_value").strip())
    # get cohort
    cohort_id = request.form.get("cohort_id")
    cohort = validate_cohort(cohort_id)

    # error checking
    validate_user_attribute(new_attribute_name, new_default_value, cohort,
                            previous_attribute_name, previous_default_value)
    # if nothing has changed, no need to make changes
    if new_attribute_name == previous_attribute_name and new_default_value == previous_default_value:
        flash("No changes were made to your custom user attribute '%s'." % previous_attribute_name.upper(), "success")
        return "success"

    # propagate changes through database
    # if default value is changed, change only on cohort level (make sure there's info on front end about this)
    if new_default_value != previous_default_value:
        # we use previous_attribute_name because we haven't changed attribute names yet
        cohort["custom_attributes"][previous_attribute_name] = new_default_value
    # if attribute name is changed, lots of places to make changes
    if new_attribute_name != previous_attribute_name:
        # change cohort custom attributes first to handle admin portal actions
        cohort["custom_attributes"][new_attribute_name] = cohort["custom_attributes"].pop(previous_attribute_name)
        cohort.save()
        # add new attribute name to user custom attributes (leave the old one in case someone is mid-survey)
        users = Users.get_for_cohort_object_id(cohort[ID_KEY])
        for user in users:
            user["custom_attributes"][new_attribute_name] = user["custom_attributes"][previous_attribute_name]
            user.save()
        # modify schedules
        for schedule in cohort.get_active_schedules():
            update_merge_fields_in_object(schedule, previous_attribute_name, new_attribute_name)
        # modify questions
        for question in Questions(cohort_id=cohort[ID_KEY]):
            update_merge_fields_in_object(question, previous_attribute_name, new_attribute_name)
        # modify conditionals
        for conditional in Conditionals(cohort_id=cohort[ID_KEY]):
            update_merge_fields_in_object(conditional, previous_attribute_name, new_attribute_name)
        # remove old attribute name in user custom attributes
        for user in users:
            user["custom_attributes"].pop(previous_attribute_name)
            user.save()
    else:
        # save cohort changes
        cohort.save()

    # return
    flash(("Your custom user attribute '%s' with default '%s' has been successfully changed to '%s' with default '%s'."
           % (previous_attribute_name.upper(), previous_default_value, new_attribute_name.upper(), new_default_value)), "success")
    return "success"


@user_management.route("/set_user_attribute", methods=["POST"])
@auth.admin
def set_user_attribute():
    user_id = request.form.get("user_id")
    attribute_name = request.form.get("attribute_name").lower().strip()
    new_value = convert_unicode(request.form.get("new_value"))
    new_value = new_value.strip()
    user = validate_user(user_id)
    cohort = user.get_cohort()
    if cohort["status"] == CohortStatus.completed:
        raise_400_error("This action is not allowed on a cohort that is already completed.")
    #Note: if you add an attribute code block here (e.g. for 'phonenum'), remember to add the attribute to FORBIDDEN_CUSTOM_ATTRIBUTES
    if attribute_name == "phonenum":
        try:
            new_value = phone_format(new_value)
        except BadPhoneNumberError:
            raise_400_error("Invalid phone number.")
        if User.exists(phonenum=new_value, cohort_id=user["cohort_id"]):
            raise_400_error("A user with phone number %s already exists in this cohort." %
                            (phonenum_humanize_filter(new_value)))
        user["phonenum"] = new_value
    elif attribute_name == "status":
        user.set_status(new_value)
        if not user["onboarded"]:
            onboard_user(user, now())
    elif attribute_name == "timezone":
        if not TIMEZONE_SUPPORT:
            raise_400_error("Changing timezones is a premium feature that is not currently enabled on your deployment.")
        else:
            user["timezone"] = new_value
    else:
        user["custom_attributes"][attribute_name] = new_value
    user.save()
    # if cohort is active and admin changed status, send message
    if attribute_name == "status" and user.get_cohort()["status"] == CohortStatus.active:
        send_status_message(user)
    return "true"


@user_management.route("/upload_user_file", methods=["POST"])
@auth.admin
def upload_user_file():
    cohort_id = request.form["cohort_id"]
    cohort = validate_cohort(cohort_id)
    if cohort["status"] == CohortStatus.completed:
        # if ajax request
        if request.is_xhr:
            flash("This action is not allowed on a cohort that is already completed.", "error")
            return jsonify({
                "reload": "true",
                "__status__": "reload"
            })
        # if normal post request
        raise_400_error("This action is not allowed on a cohort that is already completed.")
    original_number_of_custom_attributes = len(cohort.get_custom_attributes())
    user_file = request.files["user_spreadsheet"]
    if not user_file:
        flash("Please select a file to upload.", "error")
        return jsonify({
            "reload": "true",
            "__status__": "reload",
        })
    filename = secure_filename(user_file.filename)
    if PRODUCTION:
        # save uploaded file on server
        upload_path = os.path.join("/home/instantcensus/uploads/", "%s_%s" % (now().replace(microsecond=0).strftime(TS_FORMAT), filename))
        user_file.save(upload_path)
        user_file.seek(0)
    option = request.form["user_spreadsheet_upload_options"]
    errors = parse_uploaded_user_file(user_file, cohort, option)
    if errors:
        errors["__status__"] = "false"
        return jsonify(errors)
    if COHORT_USER_LIMIT:
        if Users.count(cohort_id=cohort_id) >= COHORT_USER_LIMIT:
            flash("Cohort's user limit of %s has been reached. Not all uploaded users have Instant Census system phone numbers to receive messages." % COHORT_USER_LIMIT, "error")
            return ""
    new_number_of_custom_attributes = len(cohort.get_custom_attributes())
    if original_number_of_custom_attributes != new_number_of_custom_attributes:
        reload = "true"
        flash("User upload was successful!", "success")
    else:
        reload = "false"
    return jsonify({
        "reload": reload,
        "__status__": "true"
    })


@user_management.route('/create_user', methods=["POST"])
@auth.admin
def create_user():
    #TODO: backend validation on post params
    curr_time = now()
    user_number = request.form.get("phone_number")
    cohort_id = request.form.get("cohort_id")
    cohort = validate_cohort(cohort_id)
    # check user limit
    if COHORT_USER_LIMIT:
        if Users.count(cohort_id=cohort_id) >= COHORT_USER_LIMIT:
            flash("Sorry, the user was not created because the cohort's user limit of %s has been reached." % COHORT_USER_LIMIT, "error")
            return ""
    if cohort["status"] == CohortStatus.completed:
        raise_400_error("This action is not allowed on a cohort that is already completed.")
    user = new_user_via_admin_portal(user_number, cohort[ID_KEY], curr_time)
    for item in cohort["custom_attributes"]:
        user["custom_attributes"][item] = cohort['custom_attributes'][item]
        user.save()
    flash("New user with phone number '%s' has been successfully created." % user["phonenum"], "success")
    return "success"


@user_management.route("/_get_users", methods=["POST"])
@auth.admin
def _get_users():
    cohort_id = request.form.get("cohort_id")
    cohort = validate_cohort(cohort_id)
    cohort_object_id = ObjectId(cohort_id)
    
    page_size = int(request.form.get("length", 25))
    page = int(request.form.get("start", 0)) / page_size
    
    # Default kwargs for querying all users
    users_search_kwargs = {
        "cohort_id": cohort_object_id,
    }
    if not SHOW_DELETED_USERS:
        users_search_kwargs["status"] = EXCLUDE_DELETED_USERS_QUERY
    
    # Check total number of users before filtering
    total_number_of_users = Users.count(**users_search_kwargs)
    
    # If there is a search, we need to check total number of users in search
    search_term = request.form.get("search[value]", None)
    if search_term:
        # This currently only supports searching phone number
        users_search_kwargs["phonenum"] = {"$regex": ".*{}.*".format(search_term)}
    total_number_of_users_filtered = Users.count(**users_search_kwargs)
    
    # Now we paginate to actually return data to the frontend
    users_search_kwargs.update({
        "page": page,
        "page_size": page_size,
    })
    
    users = Users(**users_search_kwargs)
    
    data = {
        "data": [],
        "draw": request.form.get("draw"),
        "recordsTotal": total_number_of_users,
        "recordsFiltered": total_number_of_users_filtered,
    }
    for user in users:
        # sms
        sms = ('<a href="/%s/send/%s">' +
                   '<span class="glyphicon glyphicon-send" aria-hidden="true"' +
                   '      title="View message history and send messages" data-toggle="tooltip">' +
                   '</span>' +
               '</a>') % (cohort_id, user["_id"])
        if cohort["status"] != CohortStatus.completed:
            sms += ('<a href="javascript:void(0);" onclick="launchDeleteUser(\'%s\')">' +
                        '<span class="glyphicon glyphicon-remove indent-1 delete" aria-hidden="true"' +
                        '      title="Delete user" data-toggle="tooltip">' +
                        '</span>' +
                    '</a>') % (user["_id"])
        # phone number
        phone_number = phonenum_humanize_filter(user["phonenum"])
        # status
        status = user["status"]
        # timezone
        timezone = user["timezone"]
        # custom attributes
        custom_attributes = []
        for attribute in sorted(cohort["custom_attributes"]):
            user_attribute_value = user["custom_attributes"][attribute] if attribute in user["custom_attributes"] \
                                   else ""
            custom_attributes.append(user_attribute_value)
        # add to current row
        data_row = [
            sms,
            phone_number,
            status,
            timezone
        ]
        data_row.extend(custom_attributes)
        # append current row to data
        data["data"].append(data_row)
    return jsonify(data)