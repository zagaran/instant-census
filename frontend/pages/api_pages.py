from flask import Blueprint, send_file
from mongolia import ID_KEY

from database.tracking.users import Users
from frontend import auth
from backend.admin_portal.download_data_helpers import generate_users_csv
from backend.admin_portal.common_helpers import validate_cohort
from constants.download_data import TS_FORMAT
from utils.time import now


api_pages = Blueprint('api_pages', __name__)


@api_pages.route("/api/v1/download_cohort_users/<cohort_id>", methods=["GET"])
@auth.api
def download_current_users(cohort_id):
    # validate cohort
    cohort = validate_cohort(cohort_id)
    # timestamp for file name
    timestamp = now().replace(microsecond=0).strftime(TS_FORMAT)
    return send_file(
         generate_users_csv(cohort),
         attachment_filename="cohort_users/cohort_(%s)_users_%s.csv" % (cohort["cohort_name"], timestamp),
         as_attachment=True
    )
