from bson import ObjectId
from flask import flash, abort, session
from mongolia import ID_KEY

from constants.cohorts import CohortStatus
from database.backbone.cohorts import Cohort, Cohorts
from database.tracking.users import User


#cohort_name_pattern = compile(r"[^ \w-]+")  # allows alphanumeric, dashes, underscores, spaces
COHORT_NAME_MAX_LENGTH = 100


def validate_cohort(cohort_id):
    # if str
    if not isinstance(cohort_id, ObjectId):
        # if invalid cohort id
        if len(cohort_id) != 24:
            raise_404_error("Invalid Cohort ID.")
        cohort = Cohort(ObjectId(cohort_id))
    else:
        cohort = Cohort(cohort_id)
    # if cohort not found
    if not cohort:
        raise_404_error("Cohort not found.")
    # return cohort
    return cohort


def validate_user(user_id):
    # if str
    if not isinstance(user_id, ObjectId):
        # if invalid user id
        if len(user_id) != 24:
            raise_404_error("Invalid User ID.")
        user = User(ObjectId(user_id))
    else:
        user = User(user_id)
    # if user not found
    if not user:
        raise_404_error("User not found.")
    # return user
    return user


def validate_cohort_id_match(user_cohort_id, cohort_id):
    if user_cohort_id != cohort_id:
        raise_404_error("This user does not belong to this cohort.")


def check_inactive_limit(inactive_limit):
    try:
        inactive_limit = int(inactive_limit)
        if not isinstance(inactive_limit, int):
            raise ValueError
    except ValueError:
        raise_400_error("Invalid Inactive Limit. The limit must be a number.")
    return inactive_limit

def check_area_code(area_code):
    if area_code == "" or area_code.lower() == "none":
        area_code = None
    else:
        try:
            # int cast throws error
            area_code = int(area_code)
            # check against if the int is actually long & if len is 3
            if not isinstance(area_code, int) or len(str(area_code)) != 3:
                raise ValueError
        except ValueError:
            raise_400_error("Invalid Area Code. Area codes must be comprised of 3 digits.")
    return area_code

def check_welcome_message(welcome_message):
    #TODO: implement
    return welcome_message

def check_cohort_name(cohort_name, existing_id=None):
    cohort_name = cohort_name[:COHORT_NAME_MAX_LENGTH]
    # Check if a cohort already exists with such a name
    conflicting_cohorts = [cohort for cohort in Cohorts(cohort_name=cohort_name, customer_id=ObjectId(session["customer_id"])) 
                        if cohort["status"] != CohortStatus.deleted and cohort[ID_KEY] != existing_id]
    if len(conflicting_cohorts) > 0:
        raise_400_error("Invalid cohort name. Another cohort has the same name.")
    return cohort_name
    


def raise_400_error(message, category="danger"):
    flash(message, category)
    abort(400)

def raise_404_error(message, category="danger"):
    flash(message, category)
    abort(404)
