import json
import uuid
from datetime import datetime

from bson import ObjectId
from flask import Blueprint, request, redirect, flash, abort, session
from mongolia.constants import ID_KEY

from backend.admin_portal.common_helpers import (validate_cohort, raise_400_error)
from backend.admin_portal.survey_builder_helpers import (validate_and_unpack,
    check_date, item_finder, update_database_object, update_action,
    check_for_forbidden, check_text, deleter, remove_from_parent, add_to_parent,
    enact_move, validate_question_data, check_attributes, validate_schedule, choices_append,
    manually_run_schedule_core, schedule_comparitor,
    recursive_attribute_check, test_schedule_core, update_conditionals)
from backend.outgoing.message_builder import merge_in_custom_attributes
from conf.settings import ENABLE_FAST_FORWARD, ENABLE_SCHEDULE_TESTING, DISABLE_LENGTH_RESTRICTION
from constants.cohorts import CohortStatus, FORBIDDEN_CUSTOM_ATTRIBUTES
from constants.database import ANSWER_VALUE, ANSWER_VALUE_DISPLAY
from constants.messages import MULTIPLE_CHOICE_RESEND_TEXT
from constants.parser_consts import FORBIDDEN_WORDS
from database.backbone.cohorts import Cohorts
from database.backbone.schedules import (Schedule, Conditional, Question, Schedules)
from database.tracking.schedule_execution import ScheduleExecutions
from database.tracking.users import Users, User
from frontend import auth, templating
from utils.formatters import convert_unicode
from utils.time import now

survey_builder = Blueprint('survey_builder', __name__)


@survey_builder.route('/<cohort_id>/surveys', methods=["GET", "POST"])
@auth.admin
@templating.template('admin_portal/survey_builder.html')
def render_survey_builder(cohort_id):
    cohort = validate_cohort(cohort_id)
    cohorts = Cohorts.retrieve_by_admin(ObjectId(session["admin_id"]))
    noncomplete_cohorts = [coh for coh in cohorts if coh["status"] != "completed"]
    #these two lists have guaranteed order.
    cohort_ids = [str(c[ID_KEY]) for c in noncomplete_cohorts]
    cohort_names = [str(c["cohort_name"]) for c in noncomplete_cohorts]
    cohort_user_numbers = Users(cohort_id=cohort[ID_KEY], field="phonenum")
    cohort_user_numbers = json.dumps(cohort_user_numbers, ",")
    
    return {
        "cohort": cohort,
        "cohort_ids_python": cohort_ids,
        "cohort_names_python": cohort_names,
        "COHORT_COMPLETED": cohort["status"] == CohortStatus.completed,
        "custom_attributes": cohort["custom_attributes"],
        "FORBIDDEN_MULTIPLE_CHOICE_ANSWERS": json.dumps(FORBIDDEN_WORDS),
        "FORBIDDEN_CUSTOM_ATTRIBUTES": json.dumps(FORBIDDEN_CUSTOM_ATTRIBUTES),
        "page": "surveys",
        "schedules": sorted(cohort.serialized_schedules(), cmp=schedule_comparitor),
        "COHORT_USER_NUMBERS": cohort_user_numbers,
        "ENABLE_FAST_FORWARD": ENABLE_FAST_FORWARD,
        "ENABLE_SCHEDULE_TESTING": ENABLE_SCHEDULE_TESTING,
        "MULTIPLE_CHOICE_RESEND_TEXT": MULTIPLE_CHOICE_RESEND_TEXT,
        "DISABLE_LENGTH_RESTRICTION": DISABLE_LENGTH_RESTRICTION,
        "ANSWER_VALUE": ANSWER_VALUE,
        "ANSWER_VALUE_DISPLAY": ANSWER_VALUE_DISPLAY
    }


@survey_builder.route('/create_new_item', methods=["POST"])
@auth.admin
def create_new_item():
    cohort_id = request.form.get("cohort_id")
    cohort = validate_cohort(cohort_id)
    if cohort["status"] == CohortStatus.completed:
        raise_400_error("This action is not allowed on a cohort that is already completed.")
    cohort_id = cohort[ID_KEY]
    item_type = request.form.get("type")
    data = validate_and_unpack(request.form.get('data'))
    data["cohort_id"] = cohort_id
    if item_type == "schedule":
        if "date" in data:
            date = datetime.strptime(data["date"], '%Y-%m-%d')
            data["date"] = date
        check_date(data, item_type)
        schedule = Schedule.create(random_id=True, data=data)
        return_value = True
    elif item_type == "send_question":
        parent_id = ObjectId(request.form.get("parent"))
        parent_type = request.form.get("parent_type")
        data["choices_append"] = choices_append(data)
        check_for_forbidden(data)
        check_attributes(data, cohort)
        if "text" in data:
            check_text(data, item_type)
            data["text"] = convert_unicode(data["text"])
        data = validate_question_data(data)
        item = Question.create(random_id=True, data=data)
        return_value = add_to_parent(item_type, {"database_id": item[ID_KEY]}, parent_id, parent_type)
    elif item_type == "conditional":
        parent_id = ObjectId(request.form.get('parent'))
        parent_type = request.form.get('parent_type')
        if "comparison" in data:
            data["comparison"] = convert_unicode(data["comparison"])
        item = Conditional.create(random_id=True, data=data)
        return_value = add_to_parent(item_type, {'database_id': item[ID_KEY]}, parent_id, parent_type)
    elif item_type in ["send_message", "set_attribute"]:
        parent_id = ObjectId(request.form.get('parent'))
        parent_type = request.form.get('parent_type')
        del data["cohort_id"]
        check_attributes(data, cohort)
        if "text" in data:
            check_text(data, item_type)
            data["text"] = convert_unicode(data["text"])
        if "attribute" in data:
            data["attribute"] = data["attribute"].lower()
        if "attribute_value" in data:
            data["attribute_value"] = convert_unicode(data["attribute_value"])
        return_value = add_to_parent(item_type, data, parent_id, parent_type)
    # if successful
    if return_value:
        flash("Schedule item was successfully created.", "success")
        return "success"
    # for non-valid items
    else:
        raise_400_error("You are attempting to create an invalid action.")


@survey_builder.route('/move_action', methods=["POST"])
@auth.admin
def move_action():
    cohort_id = request.form.get("cohort_id")
    cohort = validate_cohort(cohort_id)
    if cohort["status"] == CohortStatus.completed:
        raise_400_error("This action is not allowed on a cohort that is already completed.")
    direction = request.form.get("direction")
    parent = ObjectId(request.form.get('parent'))
    parent_type = request.form.get('parent_type')
    index = int(request.form.get('index'))
    if direction == "up":
        switch = index - 1
    elif direction == "down":
        switch = index + 1
    else:
        raise_400_error("Moving item failed because an invalid direction was specified.")
    parent = item_finder(parent, parent_type)
    return enact_move(parent, index, switch)


@survey_builder.route('/delete_item', methods=["POST"])
@auth.admin
def delete_item():
    cohort_id = request.form.get("cohort_id")
    cohort = validate_cohort(cohort_id)
    item_type = request.form.get("item_type")
    # error checking
    if cohort["status"] == CohortStatus.completed:
        raise_400_error("This action is not allowed on a cohort that is already completed.")
    # for schedules
    if item_type == 'schedule':
        # get schedule
        item_id = ObjectId(request.form.get("item_id"))
        schedule = Schedule(item_id)
        if schedule is None:
            raise_400_error("Invalid delete. You are attempting to delete an item that does not exist.")
        # update schedule status
        schedule.update({"deleted": True})
        # delete schedule executions
        for schedule_execution in ScheduleExecutions(schedule_id=schedule[ID_KEY]):
            schedule_execution.remove()
        return_value = True
    # for items with own class (questions and conditionals)
    elif item_type in ['send_question', 'conditional']:
        item_id = ObjectId(request.form.get("item_id"))
        parent_type = request.form.get("parent_type")
        parent_id = ObjectId(request.form.get('parent'))
        item = item_finder(item_id, item_type)
        return_value = deleter(item, item_id, parent_id, parent_type)
    # for items without own class (set attribute and send message)
    elif item_type in ['set_attribute', 'send_message']:
        item_id = uuid.UUID(request.form.get("item_id"))
        parent_type = request.form.get("parent_type")
        parent_id = ObjectId(request.form.get('parent'))
        parent = item_finder(parent_id, parent_type)
        return_value = remove_from_parent(parent, item_id)
    # if successful
    if return_value:
        flash("Schedule item(s) were successfully deleted.", "success")
        return "success"
    # for non-valid items
    else:
        raise_400_error("You are attempting to delete an item with an invalid type.")


@survey_builder.route('/modify_item', methods=["POST"])
@auth.admin
def modify_item():
    cohort_id = request.form.get("cohort_id")
    cohort = validate_cohort(cohort_id)
    if cohort["status"] == CohortStatus.completed:
        raise_400_error("This action is not allowed on a cohort that is already completed.")
    cohort_id = cohort[ID_KEY]
    item_type = request.form.get("type")
    data = validate_and_unpack(request.form.get('data'))
    data["cohort_id"] = cohort_id
    if item_type in ['schedule', 'conditional']:
        item_id = ObjectId(request.form.get('item_id'))
        if "date" in data:
            data["date"] = datetime.strptime(data["date"], '%Y-%m-%d')
        check_date(data, item_type)
        item = item_finder(item_id, item_type)
        if item_type == "schedule" and update_database_object(item, data):
            item._update_schedule_executions(now())
            return "true"
        else:
            return update_database_object(item, data)
    elif item_type in ["send_message", "set_attribute"]:
        item_id = uuid.UUID(request.form.get('item_id'))
        parent_id = ObjectId(request.form.get('parent'))
        parent_type = request.form.get('parent_type')
        del data["cohort_id"]
        check_attributes(data, cohort)
        if "text" in data:
            check_text(data, item_type)
            data["text"] = convert_unicode(data["text"])
        return update_action(item_id, item_type, data, parent_id, parent_type)
    elif item_type == 'send_question':
        item_id = ObjectId(request.form.get('item_id'))
        if 'auto_append' in data:
            data['choices_append'] = choices_append(data)
        check_for_forbidden(data)
        check_attributes(data, cohort)
        if "text" in data:
            check_text(data, item_type)
            data["text"] = convert_unicode(data["text"])
        item = item_finder(item_id, item_type)
        data = validate_question_data(data)
        update_conditionals(data, item)
        return update_database_object(item, data)
    raise_400_error("Invalid Action Type. You are attempting to modify an item with an invalid type.")

@survey_builder.route('/copy_all_surveys', methods=["POST"])
@auth.admin
def copy_all_surveys():
    old_cohort_id = request.form.get("old_cohort_id")
    new_cohort_id = request.form.get("new_cohort_id")
    old_cohort = validate_cohort(old_cohort_id)
    new_cohort = validate_cohort(new_cohort_id)
    for sched in Schedules(cohort_id=old_cohort[ID_KEY], deleted=False):
        recursive_attribute_check(sched, new_cohort)
    for sched in Schedules(cohort_id=old_cohort[ID_KEY], deleted=False):
        sched.recursive_copy(ObjectId(new_cohort_id))
    flash("Schedules were successfully copied to %s." % new_cohort["cohort_name"], "success")
    return "success"
    

@survey_builder.route('/copy_survey', methods=["POST"])
@auth.admin
def copy_survey():
    #TODO: is order guaranteed in the list of cohorts?
    id_string = request.form.get("schedule_id")
    new_cohort_id = request.form.get("new_cohort_id")
    cohort = validate_cohort(new_cohort_id)
    sched = Schedule(ObjectId(id_string))
    recursive_attribute_check(sched, cohort)
    sched.recursive_copy(ObjectId(new_cohort_id))
    flash("Schedule was successfully copied to %s." % cohort["cohort_name"], "success")
    return "success"


@survey_builder.route('/manually_run_schedule/<schedule_id>', methods=["GET", "POST"])
@auth.admin
def manually_run_schedule(schedule_id):
    if not ENABLE_FAST_FORWARD:
        abort(403)
    schedule = validate_schedule(schedule_id)
    cohort = validate_cohort(schedule["cohort_id"])
    if cohort["status"] == CohortStatus.completed:
        raise_400_error("This action is not allowed on a cohort that is already completed.")
    if cohort["status"] != CohortStatus.active:
        flash("This cohort is currently paused, so no schedule was sent.", "warning")
    else:
        curr_time = now()
        manually_run_schedule_core(schedule, cohort, curr_time)
        flash("A schedule has been manually activated and run.", "success")
    return redirect("/%s/surveys" % cohort[ID_KEY])


@survey_builder.route('/test_schedule', methods=["GET", "POST"])
@auth.admin
def test_schedule():
    if not ENABLE_SCHEDULE_TESTING:
        abort(403)
    schedule = validate_schedule(request.form.get("schedule_id"))
    cohort = validate_cohort(schedule["cohort_id"])
    if cohort["status"] == CohortStatus.completed:
        raise_400_error("This action is not allowed on a cohort that is already completed.")
    if cohort["status"] != CohortStatus.active:
        flash("This cohort is currently paused, so no schedule was sent.", "warning")
    else:
        user_numbers = json.loads(request.form.get("users"))
        users = [User.retrieve(phonenum=pn, cohort_id=cohort[ID_KEY]) for pn in user_numbers]
        curr_time = now()
        test_schedule_core(schedule, cohort, curr_time, users)
        flash("This schedule has been sent to %s users for testing" % (len(user_numbers)), "success")
    return redirect("/%s/surveys" % cohort[ID_KEY])

@survey_builder.route("/preview_item", methods=["POST"])
@auth.admin
@templating.template("admin_portal/preview_item.html")
def preview_item():
    cohort_id = request.form.get("cohort_id")
    text = request.form.get("text")
    cohort = validate_cohort(cohort_id)
    users = Users.get_for_cohort_object_id(cohort[ID_KEY])
    messages = [(user.phonenum, merge_in_custom_attributes(text, user=user)) for user in users]
    return {
        "messages": messages,
    }
