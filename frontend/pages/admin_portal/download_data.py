import time
import zipfile
from io import BytesIO

from flask import Blueprint, send_file, request
from mongolia import ID_KEY

from backend.admin_portal.common_helpers import validate_cohort, validate_user, raise_404_error
from backend.admin_portal.download_data_helpers import (generate_messages_csv,
    generate_users_csv, generate_question_answer_csv,
    generate_question_answer_summary_by_question_csv,
    generate_question_answer_summary_by_recipient_csv, get_user_messages_history)
from conf.settings import SHOW_DELETED_USERS
from constants.download_data import TS_FORMAT
from constants.users import Status
from frontend import auth
from utils.time import now

download_data = Blueprint('download_data', __name__)


@download_data.route('/download/users/<cohort_id>', methods=["GET"])
@auth.admin
def download_user_data(cohort_id):
    timestamp = now().replace(microsecond=0).strftime(TS_FORMAT)
    # validate cohort
    cohort = validate_cohort(cohort_id)
    # get users
    csv_data = generate_users_csv(cohort)
    return send_file(csv_data, as_attachment=True, attachment_filename="cohort_(%s)_users_%s.csv" % (cohort["cohort_name"], timestamp))


@download_data.route("/download/history/<user_id>", methods=["GET"])
@auth.admin
def download_message_history(user_id):
    # validate user
    user = validate_user(user_id)
    # do not download if deleted and option isn't set
    if not SHOW_DELETED_USERS and user["status"] == Status.deleted:
        raise_404_error("User not found.")
    user_messages = user.all_messages()
    timestamp = now().replace(microsecond=0).strftime(TS_FORMAT)
    csv_data = generate_messages_csv(user_messages, user["phonenum"], user["timezone"])
    return send_file(csv_data, as_attachment=True, attachment_filename="user_(%s)_messages_%s.csv" % (user["phonenum"], timestamp))


# TODO: This could be DRYed out
@download_data.route("/download/history-incoming/<user_id>", methods=["GET"])
@auth.admin
def download_incoming_message_history(user_id):
    timestamp = now().replace(microsecond=0).strftime(TS_FORMAT)
    # validate user
    user = validate_user(user_id)
    # do not download if deleted and option isn't set
    if not SHOW_DELETED_USERS and user["status"] == Status.deleted:
        raise_404_error("User not found.")
    user_messages = user.all_messages()
    # remove outgoing messages
    user_messages = [message for message in user_messages if message["incoming"] == True]
    csv_data = generate_messages_csv(user_messages, user["phonenum"], user["timezone"])
    return send_file(csv_data, as_attachment=True, attachment_filename="user_(%s)_messages_%s.csv" % (user["phonenum"], timestamp))

# these are the commands to trigger the different things.
# http://127.0.0.1:5000/download/custom/582645d1d9e34415c4f662d0?download_cohort_users=true&statuses=active,pending,invalid,waitlist,paused,disabled,inactive,&
# http://127.0.0.1:5000/download/custom/582645d1d9e34415c4f662d0?download_user_message_histories=true&type=all&
# http://127.0.0.1:5000/download/custom/582645d1d9e34415c4f662d0?download_question_answer_data=true&
@download_data.route("/download/custom/<cohort_id>", methods=["GET"])
@auth.admin
def download_data_custom(cohort_id):
    # collect GET data TODO: do we need to sanitize these inputs?
    download_cohort_users = request.args.get("download_cohort_users")
    download_user_message_histories = request.args.get("download_user_message_histories")
    download_question_answer_data = request.args.get("download_question_answer_data")
    # validate cohort
    cohort = validate_cohort(cohort_id)
    cohort_id = cohort[ID_KEY]
    # get all users
    
    # date_time (for zip file) should be a tuple containing six fields which describe the time of the file last modification
    date_time = time.localtime(time.time())[:6]
    # timestamp for file name
    timestamp = now().replace(microsecond=0).strftime(TS_FORMAT)
    # store all files to be zipped in list
    files = []
    
    if download_cohort_users == "true":
        # collect and clean GET data
        statuses_to_download_string = request.args.get("statuses")[:-1]  # since there is a trailing comma
        statuses_to_download = [element for element in statuses_to_download_string.split(",")]
        # remove deleted status if option not set
        if not SHOW_DELETED_USERS:
            statuses_to_download = [element for element in statuses_to_download if element != "deleted"]
            statuses_to_download_string = ",".join(statuses_to_download)
        # create csv and add to return
        csv_data = generate_users_csv(cohort, statuses_to_download)
        files.append({
            "file_name": "cohort_users/cohort_(%s)_users_(%s)_%s.csv" %
                         (cohort["cohort_name"], statuses_to_download_string, timestamp),
            "date_time": date_time,
            "file_data": csv_data.getvalue()
        })
        
    if download_user_message_histories == "true":
        # This function uses a lot of memory, so it has been stuck into its own function to
        # enable some memory cleanup.  get_user_messages_history isa mutator function, it modifies
        # the files variable (its a list).
        get_user_messages_history(cohort_id, files, timestamp, date_time)
        
    if download_question_answer_data == "true":
        csv_data = generate_question_answer_csv(cohort)
        files.append({
            "file_name": "questions_and_answers/cohort_(%s)_all_questions_and_answers_%s.csv" % (cohort["cohort_name"], timestamp),
            "date_time": date_time,
            "file_data": csv_data.getvalue()
        })
        summary_csv_data_by_question = generate_question_answer_summary_by_question_csv(cohort)
        files.append({
            "file_name": "questions_and_answers/cohort_(%s)_questions_and_answers_summary_by_question_%s.csv" % (cohort["cohort_name"], timestamp),
            "date_time": date_time,
            "file_data": summary_csv_data_by_question.getvalue()
        })
        summary_csv_data_by_recipient = generate_question_answer_summary_by_recipient_csv(cohort)
        files.append({
            "file_name": "questions_and_answers/cohort_(%s)_questions_and_answers_summary_by_recipient_%s.csv" % (cohort["cohort_name"], timestamp),
            "date_time": date_time,
            "file_data": summary_csv_data_by_recipient.getvalue()
        })
        
    # create zip file in memory
    memory_file = BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        for file in files:
            data = zipfile.ZipInfo(file["file_name"])
            data.date_time = file["date_time"]
            data.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(data, file["file_data"])
    # move pointer to beginning of BytesIO for send_file to read the data
    memory_file.seek(0)
    # return file to download
    return send_file(
            memory_file,
            attachment_filename="cohort_(%s)_custom_download_%s.zip" % (cohort["cohort_name"], timestamp),
            as_attachment=True
    )
    