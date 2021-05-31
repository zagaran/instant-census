from flask.blueprints import Blueprint
from flask import session

from bson import ObjectId
from mongolia import ID_KEY

from constants.cohorts import CohortStatus
from constants.database import EXCLUDE_DELETED_USERS_QUERY
from constants.users import Status, AdminTypes
from database.tracking.users import Users
from database.backbone.cohorts import Cohorts, Customer
from frontend import templating, auth
from conf.settings import SHOW_DELETED_USERS, ADMIN_LEVEL_VISIBILITY
from frontend.auth import is_admin_type

needs_review = Blueprint('needs_review', __name__)


@needs_review.route("/review")
@auth.admin
@templating.template("/admin_portal/needs_review.html")
def render_needs_review():
    customer = Customer(ObjectId(session["customer_id"]))
    # If not restricting visibility by admin or is super admin
    if not ADMIN_LEVEL_VISIBILITY or is_admin_type([AdminTypes.super]):
        # get all cohorts attached to customer
        cohorts = Cohorts.retrieve_by_customer(ObjectId(session["customer_id"]))
    else:
        # get all cohorts attached to admin only
        cohorts = Cohorts.retrieve_by_admin(ObjectId(session["admin_id"]))
    # get users in each cohort that need review and store in list
    users = {}
    for cohort in cohorts:
        kwargs = {
            "cohort_id": cohort[ID_KEY],
            "needs_review": True
        }
        if not SHOW_DELETED_USERS:
            kwargs["status"] = EXCLUDE_DELETED_USERS_QUERY
        users_needing_review = Users(**kwargs)
        # remove deleted users from needs review if option not set
        users[cohort["_id"]] = users_needing_review
    # split cohorts into completed/not completed
    completed_cohorts = [c for c in cohorts if c["status"] == CohortStatus.completed]
    non_completed_cohorts = [c for c in cohorts if c["status"] != CohortStatus.completed and users[c["_id"]]]
    non_completed_cohorts_empty = [c for c in cohorts if c["status"] != CohortStatus.completed and not users[c["_id"]]]
    return {
        "page": "needs_review",
        "completed_cohorts": completed_cohorts,
        "non_completed_cohorts": non_completed_cohorts,
        "non_completed_cohorts_empty": non_completed_cohorts_empty,
        "customer": customer,
        "users": users # not the same format as other pages
    }
