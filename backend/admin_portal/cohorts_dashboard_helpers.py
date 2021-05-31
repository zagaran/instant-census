from bson import ObjectId
from flask import session

from conf.settings import ADMIN_LEVEL_VISIBILITY
from constants.users import AdminTypes
from database.backbone.cohorts import Cohorts
from frontend.auth import is_admin_type


def retrieve_cohorts_by_admin():
    all_cohorts = Cohorts.retrieve_by_customer(ObjectId(session["customer_id"]))
    # If not restricting visibility by admin or is super admin
    if not ADMIN_LEVEL_VISIBILITY or is_admin_type([AdminTypes.super]):
        # get all cohorts attached to customer
        cohorts = all_cohorts
    else:
        # get all cohorts attached to admin only
        cohorts = Cohorts.retrieve_by_admin(ObjectId(session["admin_id"]))
    return cohorts, all_cohorts

def add_cohort_info(cohort):
    cohort_dict = dict(cohort)
    cohort_dict["get_active_user_count"] = cohort.get_active_user_count()
    cohort_dict["get_total_user_count"] = cohort.get_total_user_count()
    cohort_dict["get_unhandled_user_count"] = cohort.get_unhandled_user_count()
    cohort_dict["get_total_message_count"] = cohort.get_total_message_count()
    return cohort_dict