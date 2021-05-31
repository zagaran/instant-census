from bson import ObjectId
from backend.admin_portal.common_helpers import raise_404_error
from constants.database import INTERNAL_CUSTOMER_NAME
from database.analytics.responses import Responses
from database.backbone.cohorts import Customer, Cohorts
from database.backbone.schedules import Question, Questions
from database.tracking.admins import Admin
from flask import Blueprint, request, session, flash, redirect, json, jsonify
from frontend import templating, auth
from mongolia import ID_KEY
from mongolia.errors import NonexistentObjectError
from werkzeug.exceptions import abort

demo = Blueprint("demo", __name__)

@demo.route("/demo")
@auth.admin
@templating.template("demo.html")
def render_demo():
    # check if allowed
    admin = Admin(ObjectId(session["admin_id"]))
    customer = Customer(admin["customer_id"])
    if customer["customer_name"] != INTERNAL_CUSTOMER_NAME:
        abort(404)

    # get cohorts
    cohorts = Cohorts.retrieve_by_customer(ObjectId(session["customer_id"]))

    # get other data
    cohorts_data = {}
    for cohort in cohorts:
        cohorts_data[str(cohort[ID_KEY])] = {
            "name": cohort["cohort_name"],
            "attributes": ["status", "timezone"] + \
                          [str(attribute.upper()) for attribute in cohort["custom_attributes"]]
        }

    # get questions
    questions_dict = {}
    for question in Questions():
        questions_dict[str(question[ID_KEY])] = question["text"]

    return {
        "cohorts": json.dumps(cohorts_data),
        "questions": json.dumps(questions_dict)
    }


@demo.route("/_get_most_recent_responses", methods=["POST"])
@auth.admin
def _get_most_recent_responses():
    # get question
    question_id = request.form.get("question_id")
    if len(question_id) != 24:
        raise_404_error("No questions found.")
    question = Question(ObjectId(question_id))
    if not question:
        raise_404_error("Invalid Question ID.")
    # get responses
    responses = Responses(question_id=question[ID_KEY])
    responses = sorted(responses, cmp=by_latest_response_time_comparitor)
    # clean data
    data = []
    count = 0
    for response in responses:
        if response["answer_value"] is not None:
            data.append(response["answer_value"])
            count += 1
        if count >= 5:
            break
    # return
    return jsonify({
        "responses": data
    })


def by_latest_response_time_comparitor(a, b):
    """ Sorts by time from latest to earliest (and if no response, ignores it) """
    if a["times_of_responses"] and b["times_of_responses"]:
        if (b["times_of_responses"][-1] > a["times_of_responses"][-1]):
            return 1
        else:
            return -1
    else:
        return -1