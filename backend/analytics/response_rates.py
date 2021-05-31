from collections import defaultdict
from database.tracking.messages import Messages

def get_schedule_response_rates(schedule_id):
    incoming = defaultdict(int)
    outgoing = defaultdict(int)
    for message in Messages(schedule_id=schedule_id, incoming=True):
        incoming[message["survey_period_start"]] += 1
    for message in Messages(schedule_id=schedule_id, incoming=False):
        outgoing[message["survey_period_start"]] += 1
    return incoming, outgoing


def get_unanswered_resend_rates(schedule_id):
    pass

def get_bad_answer_resend_rates(schedule_id):
    pass
