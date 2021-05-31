from collections import defaultdict

from bson import ObjectId
from flask import Blueprint, session, json, jsonify, request
from mongolia import ID_KEY
from werkzeug.exceptions import abort

from backend.admin_portal.common_helpers import validate_cohort
from backend.admin_portal.data_reports_helpers import (return_empty_data, by_time_comparitor,
    assemble_admin_data)
from backend.admin_portal.download_data_helpers import (process_response_data)
from conf.settings import DATA_REPORTS_FEATURE, ADMIN_LEVEL_VISIBILITY
from constants.database import SKIP_VALUE
from constants.download_data import JAVASCRIPT_NULL_VALUE
from constants.users import AdminTypes
from database.analytics.responses import Responses
from database.analytics.system_load import ResponseTimes
from database.backbone.cohorts import Cohorts
from database.tracking.admins import Admin
from database.tracking.messages import Messages, ControlMessages
from database.tracking.users import Users
from frontend import templating, auth
from frontend.auth import is_admin_type
from utils.database import fast_live_untyped_iterator
from utils.logging import log_warning

data_reports = Blueprint("data_reports", __name__)

# TODO test actual performance on getting entire table versus make multiple database queries

INTERVALS = [int(60*i) for i in [0, .1, .2, .3, .4, .5, .75, 1, 1.25, 1.5, 1.75,
                                 2, 2.5, 3, 3.5, 4, 5, 6, 8, 10, 15, 20, 25, 30,
                                 45, 60, 90, 120, 180, 240]] # seconds

@data_reports.route("/data", methods=["GET"])
@auth.admin
@templating.template("/admin_portal/data_reports.html")
def render_data_reports():
    # do not show if feature is not yet released
    if not DATA_REPORTS_FEATURE:
        abort(404)

    # get cohorts
    admin = Admin(ObjectId(session["admin_id"]))
    # If not restricting visibility by admin or is super admin
    if not ADMIN_LEVEL_VISIBILITY or is_admin_type([AdminTypes.super]):
        # get all cohorts attached to customer
        cohorts = Cohorts.retrieve_by_customer(ObjectId(session["customer_id"]))
    else:
        # get all cohorts attached to admin only
        cohorts = Cohorts.retrieve_by_admin(ObjectId(session["admin_id"]))

    # get other data
    timezone = admin["timezone"]
    cohorts_data = {}
    for cohort in cohorts:
        cohorts_data[str(cohort[ID_KEY])] = {
            "name": cohort["cohort_name"],
            "attributes": ["status", "timezone"] + \
                          [str(attribute.upper()) for attribute in cohort["custom_attributes"]]
        }

    return {
        "timezone": timezone,
        "cohorts": json.dumps(cohorts_data),
        "page": "data_reports",
        "JAVASCRIPT_NULL_VALUE": JAVASCRIPT_NULL_VALUE,
        "SKIP_VALUE": SKIP_VALUE
    }

@data_reports.route("/_get_messages_report_data", methods=["POST"])
@auth.admin
def _get_messages_report_data():
    # do not show if feature is not yet released
    if not DATA_REPORTS_FEATURE:
        abort(404)
    # TODO: DRY this out
    # if not restricting visibility by admin or is super admin
    if not ADMIN_LEVEL_VISIBILITY or is_admin_type([AdminTypes.super]):
        # get all cohorts attached to customer
        cohorts = Cohorts.retrieve_by_customer(ObjectId(session["customer_id"]))
    else:
        # get all cohorts attached to admin only
        cohorts = Cohorts.retrieve_by_admin(ObjectId(session["admin_id"]))
    # if no cohorts
    if not cohorts:
        return return_empty_data("messages")
    # get post parameters
    time_range = request.form.get("time_range")
    if time_range not in ["day", "week", "month", "year"]:
        abort(500)

    # get messages
    ic_numbers = []
    for cohort in cohorts:
        ic_numbers.extend(cohort["ic_numbers"])
    
    # We have a bunch of shared query syntax, construct it all here
    messages_query = {"ic_number": {'$in': ic_numbers}}
    messages_projection = {"time": True, "incoming": True, ID_KEY: False}
    # Original code pulled in unnecessary attributes. These Queries are ~ 5x faster, and have about
    # 5x less runtime memory usage (size varies based on message lengths that are no longer returned),
    # This makes the sort ~30x faster - not sure how, but cool.
    all_messages = Messages(query=messages_query, projection=messages_projection) + \
                   ControlMessages(query=messages_query, projection=messages_projection)
    # if no messages
    if not all_messages:
        return return_empty_data("messages")
    # sort messages by time (we need reverse because pop() is o(c) but pop(0) is o(n))
    all_messages.sort(cmp=by_time_comparitor, reverse=True)

    # Set up our eventual return data structures, inject starting admin info
    incoming_data = []
    outgoing_data = []
    all_data = []
    assemble_admin_data(time_range, incoming_data, outgoing_data, all_data)
    
    # Go through all_messages and update data lists.  By using a while-loop, and pop
    # we can reduce memory usage as we go over the loop.
    i = 0
    while all_messages:
        message = all_messages.pop()
        try:
            # if message time is before interval, iterate to next message
            if message["time"] < all_data[i]["time_utc"]:
                continue
            # if message time is after interval, iterate interval index until it's in the time interval
            elif message["time"] > all_data[i+1]["time_utc"]:
                while not (all_data[i]["time_utc"] < message["time"] < all_data[i+1]["time_utc"]):
                    i += 1
            # here, message time should be in interval, so iterate counter
            all_data[i]["count"] += 1
            if message["incoming"]:
                incoming_data[i]["count"] += 1
            else:
                outgoing_data[i]["count"] += 1
        # this should never hit an error, unless there is a problem with message timestamp or this logic
        except IndexError:
            log_warning("Index out of range in _get_message_data: message %s" % message[ID_KEY])
            break
    # pop out last element in data (see earlier comment)
    incoming_data.pop(-1)
    outgoing_data.pop(-1)
    all_data.pop(-1)

    # return result
    return jsonify({
        "__status__": "success",
        "all": all_data,
        "incoming": incoming_data,
        "outgoing": outgoing_data,
    })


@data_reports.route("/_get_users_report_data", methods=["POST"])
@auth.admin
def _get_users_report_data():
    # do not show if feature is not yet released
    if not DATA_REPORTS_FEATURE:
        abort(404)

    # get post parameters
    cohort_id = request.form.get("cohort_id")
    cohort = validate_cohort(cohort_id)
    custom_attributes_list = cohort["custom_attributes"]  # this actually is a minor optimization
    data = {
        "custom_attributes": {attribute: defaultdict(int) for attribute in custom_attributes_list},
        "status": defaultdict(int),
        "timezone": defaultdict(int),
    }
    # TODO: this database query is in serious need of only getting the appropriate fields, which is not natively supported by the mongolia iterator.
    # parse users to generate data list
    for user in Users.get_for_cohort_object_id(cohort[ID_KEY], iterator=True):
        # normal attributes
        for attribute in ["status", "timezone"]:
            data[attribute][user[attribute]] += 1
        # custom attributes
        for attribute in custom_attributes_list:
            data["custom_attributes"][attribute][user["custom_attributes"][attribute]] += 1
    
    # format data
    formatted_data = {
        "__status__": "success",
        "count": Users.get_count_for_cohort_object_id(cohort[ID_KEY])
    }
    # format custom attributes
    for attribute in data["custom_attributes"]:
        attribute_upper = attribute.upper()
        formatted_data[attribute_upper] = []
        # your IDE might complain about this .iteritems() being bad, but... the code does not error here?
        for key, value in data["custom_attributes"][attribute].iteritems():
            formatted_data[attribute_upper].append({
                "label": key,
                "count": value
            })
        formatted_data[attribute_upper].sort(key=lambda x: x["label"].upper())
    data.pop("custom_attributes")
    for attribute, count in data.items():
        # format non-custom attributes
        formatted_data[attribute] = []
        for key, value in data[attribute].iteritems():
            formatted_data[attribute].append({
                "label": key,
                "count": value
            })
        formatted_data[attribute].sort(key=lambda x: x["label"].upper())
    # return result
    return jsonify(formatted_data)


def filtered_message_count(cohort_id_list):
    """ On the sixt server, a deployment with 1,536,314 messages on it, we actually ran into
    an issue where the users list was too big to pass in as a query.
    To solve this we implement a slicing of 500,000 elements per query of the users list. """
    users_list = Users(cohort_id={"$in": cohort_id_list}, field=ID_KEY)
    if len(users_list) < 500000:
        count = Messages.count(incoming=False, question_id={"$ne": None},
                               user_id={"$in": users_list})
    else:
        count = 0
        for i in xrange((len(users_list) / 500000) + 1):
            start = i * 500000
            end = start + 500000
            count += Messages.count(incoming=False, question_id={"$ne": None},
                                    user_id={"$in": users_list[start:end]})
    return count

@data_reports.route("/_get_response_time_report_data", methods=["POST"])
@auth.admin
def _get_response_time_report_data():
    # do not show if feature is not yet released
    if not DATA_REPORTS_FEATURE:
        abort(404)
    
    # TODO DRY this out
    # If not restricting visibility by admin or is super admin
    if not ADMIN_LEVEL_VISIBILITY or is_admin_type([AdminTypes.super]):
        # get all cohorts attached to customer
        cohorts = Cohorts.retrieve_by_customer(ObjectId(session["customer_id"]))
    else:
        # get all cohorts attached to admin only
        cohorts = Cohorts.retrieve_by_admin(ObjectId(session["admin_id"]))
    cohort_id_list = [cohort[ID_KEY] for cohort in cohorts]
    # if no cohorts
    if not cohorts:
        return return_empty_data("response_times")
    
    # get total number of expected responses
    expected = filtered_message_count(cohort_id_list)
    
    # if no expected responses
    if expected == 0:
        return return_empty_data("response_times")

    response_times = fast_live_untyped_iterator(
            ResponseTimes, cohort_id={"$in": cohort_id_list}, field="response_time"
    )
    # initialize needed data objects
    formatted_data = {
        "__status__": "success",
        "expected": 0,
        "response_times": []
    }
    formatted_response_times = {i: 0 for i in INTERVALS}
    # iterate through to categorize into intervals
    for response_time in response_times:
        for interval in INTERVALS:
            if response_time < interval:
                formatted_response_times[interval] += 1
                break
    # get total number of expected responses
    formatted_data["expected"] = expected
    
    # reformat data
    for key, value in formatted_response_times.items():
        formatted_data["response_times"].append({
            "time": key,
            "count": value
        })
    formatted_data["response_times"].sort(cmp=by_time_comparitor)
    return jsonify(formatted_data)


@data_reports.route("/_get_responses_report_data", methods=["POST"])
@auth.admin
def _get_responses_report_data():
    # do not show if feature is not yet released
    if not DATA_REPORTS_FEATURE:
        abort(404)

    # get cohort
    cohort_id = request.form.get("cohort_id")
    cohort = validate_cohort(cohort_id)
    # if no cohort
    if not cohort:
        return return_empty_data("responses")
    # if no response objects (since we pull question text from Responses())
    if not Responses.count(cohort_id=cohort[ID_KEY]):
        return return_empty_data("responses")
    # process data
    data = process_response_data(cohort[ID_KEY])
    # initialize needed data objects
    formatted_data = {
        "__status__": "success",
        "data": data,
    }

    return jsonify(formatted_data)