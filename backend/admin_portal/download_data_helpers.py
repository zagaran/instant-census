import cStringIO
import csv
from operator import itemgetter

from flask import request
from mongolia import ID_KEY
from mongolia.errors import NonexistentObjectError

from backend.admin_portal.question_sorter import (sorted_list_of_all_questions,
    get_survey_period_start_time)
from constants.database import SKIP_VALUE, BAD_RESPONSE_LIMIT_REACHED_VALUE
from constants.reports import CSV_NEWLINE_CHARACTERS
from database.analytics.responses import Responses
from database.backbone.schedules import Question
from database.tracking.messages import Messages, ControlMessages
from database.tracking.users import Users
from utils.database import fast_live_untyped_iterator
from utils.formatters import encode_unicode
from utils.logging import log_warning
from utils.time import convert_from_utc

process_response_data_fields = [
    "answer_value",
    "count",
    "label",
    "original_send_time",
    "question_id",
    "question_text",
]
generate_users_csv_fields = [
    ID_KEY,
    "create_time",
    "custom_attributes",
    "ic_number",
    "phonenum",
    "phonenum_status",
    "status",
    "timezone",
]

# For use in converting python backend to human-readable frontend
ANSWER_DISPLAY_FORMAT = {
    SKIP_VALUE: u"(Skipped)",
    "": u"(No Text)",
    BAD_RESPONSE_LIMIT_REACHED_VALUE: u"(Skipped)"
}

#Note, support Unicode in downlaods
#import codecs
#encoder = codecs.getincrementalencoder("utf-8")()
#encoder.encode(text.decode("utf-8"))

def generate_messages_csv(user_messages, user_phone, user_timezone):
    # write CSV to memory instead of opening and writing to file
    csv_data = cStringIO.StringIO()
    writer = csv.writer(csv_data)
    # set and write header
    header = ["UTC Timestamp", "Local Timestamp", "Recipient Timezone", "Recipient ID", "Recipient Phone Number", "Direction", "Message"]
    writer.writerow(header)
    # iterate through messages
    if len(user_messages) == 0:
        writer.writerow(["No messages"])
    else:
        for message in user_messages:
            # get data
            time = message["time"]
            local_time = convert_from_utc(message["time"], user_timezone)
            recipient_id = message["user_id"]
            direction = "outgoing"
            if message["incoming"]:
                direction = "incoming"
            text = format_answer_display(message["text"])
            # write data
            data = [time, local_time, user_timezone, recipient_id, user_phone, direction, encode_unicode("utf-8")]
            writer.writerow(data)
    # move pointer to beginning of StringIO for send_file to read the data
    csv_data.seek(0)
    return csv_data


def generate_users_csv(cohort, statuses_to_download=None):
    """ Takes a (validated) cohort object and a list of statuses.  If no status list is provided
        all data for all statuses are returned. """
    kwargs = {"projection": generate_users_csv_fields, "iterator": True}
    if statuses_to_download is not None:
        kwargs["status"] = {"$in": statuses_to_download}
    users = Users.get_for_cohort_object_id(cohort[ID_KEY], **kwargs)
    
    csv_data = cStringIO.StringIO()
    writer = csv.writer(csv_data)
    # set and write header
    custom_attributes = cohort["custom_attributes"]
    custom_attribute_keys = custom_attributes.keys()
    header = [
        "Cohort Name",
        "Recipient ID", 
        "Recipient Creation Time (UTC)", 
        "Recipient Creation Time (Local)", 
        "Recipient Timezone", 
        "Recipient Phone Number", 
        "System Number", 
        "Recipient Status", 
        "Recipient Phone Number Status"
    ] + [encode_unicode(i).upper() for i in custom_attribute_keys] # .upper() is on purpose, for display to user
    writer.writerow(header)
    # iterate through users
    i=0
    for user in users:
        data = [
            cohort["cohort_name"],
            user["_id"],
            user["create_time"],
            convert_from_utc(user["create_time"], user["timezone"]),
            user["timezone"],
            user["phonenum"],
            user["ic_number"],
            user["status"],
            user["phonenum_status"]
        ]
        for key in custom_attribute_keys:
            if key in user["custom_attributes"]:
                # remove unicode, as csv writer only writes str
                data.append(format_answer_display(user["custom_attributes"][key]))
            elif key in cohort["custom_attributes"]:
                data.append(format_answer_display(cohort["custom_attributes"][key]))
            else:
                data.append("")
        # datas.append(data)
        writer.writerow(data)
    else:
        writer.writerow(["No users"])
    csv_data.seek(0)
    return csv_data


def generate_question_answer_csv(cohort):
    csv_data = cStringIO.StringIO()
    writer = csv.writer(csv_data)
    # set and write header
    header = [
        "Question ID",
        "Question Text (pre-merge)",
        "Question Text (merged)",
        "Question Send Time (UTC)",
        "Question Send Time (Local)",
        "Recipient Timezone",
        "Recipient Phone Number",
        "Answer"
    ]
    writer.writerow(header)
    # projections to optimize queries + readability
    users_projection = {'timezone': True, 'phonenum': True, ID_KEY: False}
    responses_projection = ["answer_value","message_ids","original_send_time","question_id","question_text","user_id"]
    # get data...
    responses = Responses(cohort_id=cohort[ID_KEY], projection=responses_projection, page_size=50000)
    responses.sort(key=lambda x: x["question_id"])
    # iterate through Responses on this cohort.  Two extra, optimized, database calls per response.
    for response in responses:
        # It is possible to pull in users and messages with 0 results, that means there is no
        # data for that event.  response["message_ids"][0] should also be handled by the
        # try-except, and its okay to continue in that situation too.
        try:
            user = Users(_id=response["user_id"], projection=users_projection)[0]
            message_text = Messages(_id=response["message_ids"][0], field="text")[0]
        except IndexError:
            continue
        writer.writerow([
            response["question_id"],
            encode_unicode(response["question_text"]),
            encode_unicode(message_text),
            response["original_send_time"],
            convert_from_utc(response["original_send_time"], user['timezone']),
            user['timezone'],
            user['phonenum'],
            format_answer_display(response["answer_value"]),
        ])
    else:
        writer.writerow(["No questions have been asked yet"])
    csv_data.seek(0)
    return csv_data


def generate_question_answer_summary_by_question_csv(cohort):
    csv_data = cStringIO.StringIO()
    writer = csv.writer(csv_data)
    # set and write header
    header = [
        "Question ID",
        "Question Text (pre-merge)",
        "Answer",
        "Number of Responses"
    ]
    writer.writerow(header)
    data = process_response_data(cohort[ID_KEY])
    for key, value in data.items():
        question_text = value["question_text"]
        for answer_value in value["responses"]:
            writer.writerow([
                key,
                question_text,
                answer_value["label"],
                answer_value["count"]
            ])
        writer.writerow([])
    csv_data.seek(0)
    return csv_data


def generate_question_answer_summary_by_recipient_csv(cohort):
    csv_data = cStringIO.StringIO()
    writer = csv.writer(csv_data)
    
    sorted_question_list = sorted_list_of_all_questions(cohort)
    question_user_response_mapping = get_question_user_response_mapping(cohort)
    # write headers
    row_1 = ["Scheduled Survey Start", ""]
    row_2 = ["Question ID", ""]
    row_3 = ["Question Text", ""]
    row_4 = ["Recipient ID", "Recipient Phone Number"]
    for question_instance in sorted_question_list:
        survey_period_start = question_instance[0]
        question_id = question_instance[1]
        row_1.extend([survey_period_start, "", "", ""])
        row_2.extend([question_id, "", "", ""])
        row_3.extend([get_question_text(question_id), "", "", ""])
        row_4.extend(["Answer", "Sent at", "Answered at", "Response time (s)"])
    writer.writerow(row_1)
    writer.writerow(row_2)
    writer.writerow(row_3)
    writer.writerow(row_4)
    # write user rows
    for user in Users(cohort_id=cohort[ID_KEY]):
        user_id = user[ID_KEY]
        row = [str(user_id), user["phonenum"]]
        for question_instance in sorted_question_list:
            if user_id in question_user_response_mapping[question_instance]:
                response = question_user_response_mapping[question_instance][user_id]
                row.append(format_answer_display(response['answer_value']))
                row.append(response['original_send_time'])
                row.append(get_response_timestamp(response))
                row.append(response['total_response_time'])
            else:
                row.extend(["(Not asked)", "", "", ""])
        writer.writerow(row)

    csv_data.seek(0)
    return csv_data


def get_question_text(question_id):
    """ Get the text of the question. If the question isn't in the database (as
    happens when the question is deleted from the survey builder), get the
    question text from a response object associated with the deleted question.
    """
    try:
        return encode_unicode(Question(question_id)['text'])
    except NonexistentObjectError:
        return encode_unicode(Responses(question_id=question_id)[0]['question_text'])


def get_response_timestamp(response):
    if len(response['times_of_responses']) > 0:
        return response['times_of_responses'][-1]
    else:
        return "N/A"


# map response objects to question_id and user_id
def get_question_user_response_mapping(cohort):
    mapping = {}
    for response in Responses(cohort_id=cohort[ID_KEY]):
        try:
            survey_period_start = get_survey_period_start_time(response)
        except NonexistentObjectError:
            log_warning(
                    "get_survey_period_start_time failed for response %s" % str(response[ID_KEY])
            )
        question_id = response["question_id"]
        user_id = response["user_id"]
        if (survey_period_start, question_id) not in mapping:
            mapping[(survey_period_start, question_id)] = {}
        mapping[(survey_period_start, question_id)][user_id] = response
    return mapping


def process_response_data(cohort_id):
    response_objects = fast_live_untyped_iterator(
            Responses, cohort_id=cohort_id, projection=process_response_data_fields
    )
    data = {}
    for response in response_objects:
        question_id = str(response["question_id"])
        question_text = encode_unicode(response["question_text"])
        answer_value = format_answer_display(response["answer_value"])
        question_text_date = response["original_send_time"]
        if question_id not in data:
            data[question_id] = {"responses": []}
        if ("question_text" not in data[question_id] or
            data[question_id]["question_text_date"] < question_text_date):
            data[question_id]["question_text"] = question_text
            data[question_id]["question_text_date"] = response["original_send_time"]

        question_responses = [r["label"] for r in data[question_id]["responses"]]
        if answer_value not in question_responses:
            data[question_id]["responses"].append({"label": answer_value, "count": 1})
        else:
            for response in data[question_id]["responses"]:
                if response["label"] == answer_value:
                    response["count"] += 1
                    break
    # sort
    for cohort_id in data:
        data[cohort_id]["responses"].sort(key=lambda x: x["count"], reverse=True)
    return data


def format_answer_display(answer_value):
    if isinstance(answer_value, int):
        return answer_value
    if answer_value is None:
        return u"(Not Answered)"
    else:
        # at this point we know its a string.
        answer_value = answer_value.replace('\n', ' ')
    if answer_value in ANSWER_DISPLAY_FORMAT:
        return ANSWER_DISPLAY_FORMAT[answer_value]
    return encode_unicode(answer_value)


def get_user_messages_history(cohort_id, files, timestamp, date_time):
    type_to_download = request.args.get("type")
    combined_csv_data = cStringIO.StringIO()
    # get data
    users = Users.get_for_cohort_object_id(cohort_id, iterator=True,
                                           projection=[ID_KEY, "phonenum", "timezone"])
    
    filter_kwargs = {"projection": ["incoming", "text", "time", "user_id"]}
    if type_to_download:
        filter_kwargs["incoming"] = True
    
    # for user in enumerfile(users, "messages_history", 2):
    for user in users:
        messages = Messages(user_id=user[ID_KEY], **filter_kwargs) +\
                   ControlMessages(user_id=user[ID_KEY], **filter_kwargs)
        messages.sort(key=itemgetter("time"))
        # if incoming only, remove outgoing messages
        csv_data = generate_messages_csv(messages, user["phonenum"], user["timezone"])
        # write file
        files.append({
            "file_name": "user_messages/user_(%s)_messages_(%s)_%s.csv" % (
            user["phonenum"], type_to_download, timestamp),
            "date_time": date_time,
            "file_data": csv_data.getvalue()
        })
        # for combined csv, move start point to NOT include headers if already written (this is kinda hacky)
        if len(combined_csv_data.getvalue()) != 0:
            offset = csv_data.getvalue().find(
                CSV_NEWLINE_CHARACTERS)  # locate where the next row starts
            offset += len(CSV_NEWLINE_CHARACTERS)  # to account for the characters themselves
            csv_data.seek(offset)
        combined_csv_data.write(csv_data.read())
    # write file
    combined_csv_data.seek(0)
    files.append({
        "file_name": "user_messages/_compiled_user_messages_(%s)_%s.csv" % (
        type_to_download, timestamp),
        "date_time": date_time,
        "file_data": combined_csv_data.getvalue()
    })