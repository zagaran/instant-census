from datetime import timedelta

from bson import ObjectId
from dateutil.relativedelta import relativedelta
from flask import session, jsonify

from database.tracking.admins import Admin
from utils.time import now, convert_to_utc, convert_from_utc


def clean_message(message):
    if "question_id" in message and message["question_id"]:
        question_id = str(message["question_id"])
    else:
        question_id = ""
    cleaned_message = {
        "ic_number": message["ic_number"],
        "incoming": message["incoming"],
        "time": message["time"],
        "question_id": question_id
    }
    return cleaned_message


def clean_user(user):
    cleaned_user = {
        "custom_attributes": user["custom_attributes"],
        "needs_review": "Needs Review" if user["needs_review"] else "OK",
        "status": user["status"],
        "timezone": user["timezone"],
    }
    return cleaned_user


def clean_response_time(response_time):
    cleaned_response_time = {
        "question_id": str(response_time["question_id"]),
        "response_time": response_time["response_time"],
        "store_date": response_time["store_date"]
    }
    return cleaned_response_time


def clean_schedule(schedule):
    cleaned_schedule = {
        "subtype": schedule["subtype"],
        "send_hour": schedule["send_hour"],
        "question_days_of_week": schedule["question_days_of_week"],
        "date": schedule["date"],
    }
    return cleaned_schedule


def by_time_comparitor(a, b):
    """ Sorts by time from earliest to latest (currently only supports sorting by [{"time": [VALUE] }]) """
    if (b["time"] < a["time"]):
        return 1
    else:
        return -1


def return_empty_data(section):
    """ Returns empty data set for ajax request depending on section """
    empty = {
        "__status__": "success",
    }
    if section == "messages":
        empty.update({
            "all": [],
            "incoming": [],
            "outgoing": [],
        })
    elif section == "response_times":
        empty.update({
            "expected": 0,
            "response_times": []
        })
    elif section == "responses":
        empty.update({
            "data": {
                "__none__": {
                    "question_text": "(No questions with responses currently available)",
                    "responses": []
                }
            }
        })
    return jsonify(empty)

def construct_range_properties(current_time_local):
    # this must be initalized here to take into account admin's current_time_local
    return {
        "day": {
            "interval": timedelta(hours=1),
            "range": timedelta(days=1),
            "rounding": timedelta(minutes=current_time_local.minute,
                                  seconds=current_time_local.second,
                                  microseconds=current_time_local.microsecond)  # to nearest hour
        },
        "week": {
            "interval": timedelta(hours=6),
            "range": timedelta(weeks=1),
            "rounding": timedelta(hours=current_time_local.hour % 6,
                                  minutes=current_time_local.minute,
                                  seconds=current_time_local.second,
                                  microseconds=current_time_local.microsecond)  # to nearest 6 hours
        },
        "month": {
            "interval": timedelta(days=1),
            "range": relativedelta(months=1),
            "rounding": timedelta(hours=current_time_local.hour,
                                  minutes=current_time_local.minute,
                                  seconds=current_time_local.second,
                                  microseconds=current_time_local.microsecond)  # to nearest day
        },
        "year": {
            "interval": relativedelta(months=1),
            "range": relativedelta(years=1),
            "rounding": timedelta(days=(current_time_local.day - 1),
                                  # since we want 1st, not 0th, of the month
                                  hours=current_time_local.hour,
                                  minutes=current_time_local.minute,
                                  seconds=current_time_local.second,
                                  microseconds=current_time_local.microsecond)  # to nearest month
        }
    }

def assemble_admin_data(time_range, incoming_data, outgoing_data, all_data):
    admin_timezone = Admin(ObjectId(session["admin_id"]))["timezone"]
    current_time_utc = now()
    current_time_local = convert_from_utc(current_time_utc, admin_timezone)
    # this must be initalized here to take into account admin's current_time_local
    range_properties = construct_range_properties(current_time_local)
    time_period_start = current_time_local - range_properties[time_range]["rounding"] -\
                        range_properties[time_range]["range"]
    time_period_position = time_period_start  # current position
    time_period_counter = 0  # initialize counter
    time_period_end = current_time_local
    # initialize data lists
    while time_period_position < time_period_end:
        # iterate counter and position first
        # Note: This will give us one additional month we don't want in the report, but we do want when we're comparing
        # message times to the intervals. For example, adding a datetime month from the last day of February should
        # yield the last day of March, but instead we get February 28 -> March 28. So we fix this by having the i+1
        # date on the interval for comparison, and pop it out at the end)
        time_period_counter += 1
        time_period_position = time_period_start + (
                    time_period_counter * range_properties[time_range]["interval"])
        # append data
        incoming_data.append({
            "time": time_period_position,
            "time_utc": convert_to_utc(time_period_position, admin_timezone),
            "count": 0
        })
        outgoing_data.append({
            "time": time_period_position,
            "time_utc": convert_to_utc(time_period_position, admin_timezone),
            "count": 0
        })
        all_data.append({
            "time": time_period_position,
            "time_utc": convert_to_utc(time_period_position, admin_timezone),
            "count": 0
        })