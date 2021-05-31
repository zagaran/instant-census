from socket import gethostname
from mongolia import ID_KEY

from constants.cohorts import CohortStatus
from constants.users import Status
from database.backbone.cohorts import Cohorts
from dateutil.relativedelta import relativedelta
from database.tracking.messages import ControlMessages, Messages
from database.tracking.users import Users
from utils.email_utils import send_eng_html
from utils.logging import log_error
from utils.time import now
from utils.server import MyICNumbers
from utils.twilio_utils import TWILIO_CLIENT

def send_billing_report_by_cohort():
    ####################################################################################################################
    ################################### COHORT-LEVEL BILLING FOR DEPLOYMENT ############################################
    ####################################################################################################################
    total_sms_messages_across_cohorts = 0
    # get previous month time range
    end_of_month = now()
    start_of_month = end_of_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - relativedelta(months=1)
    # start message
    hostname = gethostname()
    # email body
    email_body = ("Monthly Billing (by cohort) for %s <br />" % hostname +
                  "<p>Billing cycle between %s UTC and %s UTC" % (start_of_month, end_of_month) +
                  "<br /><br />")
    cohort_messages_dict = {
        CohortStatus.active: [],
        CohortStatus.paused: [],
        CohortStatus.completed: [],
        CohortStatus.deleted: [],
        CohortStatus.pending: []
    }
    # database queries, TODO: optimize
    for cohort in Cohorts():
        # all users
        all_users = Users(cohort_id=cohort[ID_KEY])
        user_ids = [user[ID_KEY] for user in all_users]
        # messages for this cohort
        messages = [m for m in Messages()
                    if (start_of_month < m["time"] < end_of_month)
                    and (m["user_id"] in user_ids)]
        control_messages = [c for c in ControlMessages()
                            if (start_of_month < c["time"] < end_of_month)
                            and (c["user_id"] in user_ids)]
        all_messages = messages + control_messages
        # users for this cohort
        # TODO: refactor once we know which user counts to track
        # get users that have sent or received at least one message this previous month in this cohort
        active_users_from_messages = set(m["user_id"] for m in all_messages if m["user_id"] in user_ids)
        # get all users that have active status
        active_users_from_statuses = [u[ID_KEY] for u in all_users if u["status"] not in [Status.deleted]]
        # get users with active phone numbers
        active_users_with_numbers = [u[ID_KEY] for u in all_users if u["ic_number"] in cohort["ic_numbers"]]
        # get users with active phone numbers that don't have deleted or disabled status
        users_with_numbers_with_active_status = [u[ID_KEY] for u in all_users
                                                 if (u["ic_number"] in cohort["ic_numbers"])
                                                 and (u["status"] not in [Status.deleted])]
        # user combinations
        combined_users = active_users_from_messages | set(active_users_from_statuses) | set(active_users_with_numbers)
        combined_users_better = active_users_from_messages | set(users_with_numbers_with_active_status)

        # TODO: this is a slow call; makes per Message object call to Twilio API to get SMS messages used for that Message
        total_messages_count = 0
        for m in all_messages:
            try:
                twilio_msg = TWILIO_CLIENT.messages.get(m.twilio_message_sid)
                total_messages_count += int(twilio_msg.num_segments)
            except Exception as e:
                # in error, assume 1 SMS
                log_error(e)
                total_messages_count += 1
        total_sms_messages_across_cohorts += total_messages_count
        highest_user_count = max(len(combined_users_better), len(combined_users), len(active_users_with_numbers),
                                 len(active_users_from_statuses), len(active_users_from_messages))
        # get message
        message = ("Total SMS Messages : %s<br />" % total_messages_count +
                   "Total Users: %s<br />" % highest_user_count)
        # add to unsorted cohort messages
        cohort_messages_dict[cohort["status"]].append({
            "cohort_id": cohort[ID_KEY],
            "cohort_name": cohort["cohort_name"],
            "message": message
        })
    # sort cohort messages alphabetically
    for status, cohort_messages in cohort_messages_dict.items():
        cohort_messages_dict[status] = sorted(cohort_messages, key=lambda x: x["cohort_name"])
    # append to email body by status
    for status in [CohortStatus.active, CohortStatus.paused, CohortStatus.completed,
                   CohortStatus.deleted, CohortStatus.pending]:
        # add cohort status header
        email_body = ("%s <hr /><hr /><h2>%s Cohorts:</h2><hr /><hr />" % (email_body, status.title()))
        # iterate through messages and append
        for entry in cohort_messages_dict[status]:
            email_body = ("%s<br /><br /><hr /><b>Cohort Name:</b> \"%s\"<br /><b>Cohort Id:</b> \"%s\"<hr /><br />%s"
                          % (email_body, entry["cohort_name"], entry["cohort_id"], entry["message"]))
    # send message
    send_eng_html("Monthly Billing (by cohort) for %s" % hostname, email_body)

    ####################################################################################################################
    ########################################### TOTAL BILLING FOR DEPLOYMENT ###########################################
    ####################################################################################################################
    # The logic below was previously `send_billing_report`
    ###TODO:
    """
    The following criterion describes 'active' users for the month: did they have an IC number at any point in the month?
    Billing logic should be rewrote to accomodate the above.

    We bill for users (indirectly for phone numbers) and messages
    """
    ###

    # bill for messages, cross validate with Twilio
    messages = [m for m in Messages() if start_of_month < m.time < end_of_month]
    control_messages = [c for c in ControlMessages() if start_of_month < c.time < end_of_month]
    total_messages = messages + control_messages
    phonenumbers = MyICNumbers()
    all_users = Users()
    # get users that have sent or received at least one message this previous month
    users_from_messages = set(t.user_id for t in total_messages)
    # get users with active phone numbers
    users_with_numbers = [u[ID_KEY] for u in all_users if u.ic_number in phonenumbers]
    # get users with active phone numbers that don't have deleted or disabled status
    #FIXME: do not include Status.deleted, Status.pending, Status.waitlist past their latest active month
    users_with_numbers_with_active_status = [u[ID_KEY] for u in all_users if (u.ic_number in phonenumbers) and (u.status != Status.deleted)]
    combined_users = users_from_messages | set(users_with_numbers_with_active_status)
    # get counts
    phonenumbers_count = len(phonenumbers)
    total_messages_count = len(total_messages)
    active_users_from_messages_count = len(users_from_messages)
    users_with_numbers_count = len(users_with_numbers)
    combined_users_count = len(combined_users)
    # send message
    send_eng_html("Monthly Billing for %s" % hostname,
                  ("Monthly Billing for %s between %s UTC and %s UTC" % (hostname, start_of_month, end_of_month) +
                   "<p>Active Phone Numbers At End of Month (only measures at end of month): %s </p>" % phonenumbers_count +
                   "<p>Total IC Messages (note this is not SMS messages): %s </p>" % total_messages_count +
                   "<p>Users having received/sent at least one message: %s </p>" % active_users_from_messages_count +
                   "<p>Users with Numbers Attached: %s </p>" % users_with_numbers_count +
                   "<p>----billing numbers below----</p>" +
                   "<p>Total SMS Messages: %s [Verify number against Twilio billing for billing] </p>" % total_sms_messages_across_cohorts +
                   "<p>Total Users: %s </p>" % combined_users_count))

