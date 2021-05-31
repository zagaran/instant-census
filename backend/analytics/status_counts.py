from __future__ import division
from datetime import datetime

from database.analytics.system_load import StatusCount, StatusCounts
from database.tracking.users import Users, Status
from database.backbone.cohorts import Cohorts
from utils.database import ID_KEY
from utils.time import now

def store_status_counts():
    """ Called by a cron job to store status counts for users across various cohorts. """
    date = now()
    cohort_ids = Cohorts(field=ID_KEY)
    statuses = [value for key, value in Status.__dict__.iteritems() if "__" not in key]
    for status in statuses:
        for cohort_id in cohort_ids:
            count = Users().count(status=status, cohort_id=cohort_id)
            StatusCount.store(status, count, cohort_id, date)

def status_count_history(status, cohort_id=None, start_date=None, end_date=None):
    """ Given a status, Returns a dictionary of dates and total counts for that status """
    start_date, end_date = date_query(start_date, end_date)
    dates = set(StatusCounts(query={"date": {"$gte": start_date, "$lte": end_date}}, field="date"))
    if cohort_id is None:
        counts = dict((date.date(), sum(StatusCounts(date=date, field="count", status=status)))
                      for date in dates)
    else:
        counts = dict((date.date(), sum(StatusCounts(date=date, field="count", status=status, cohort_id=cohort_id)))
                      for date in dates)
    return counts

def date_query(start_date, end_date):
    """Inputs a start_date and end_date"""
    if start_date is not None and not isinstance(start_date, datetime):
        raise TypeError("The start date must be either None or a datetime object")
    if end_date is not None and not isinstance(end_date, datetime):
        raise TypeError("The end date must be either None or a datetime object")
    if start_date is not None and end_date is not None and end_date < start_date:
        raise ValueError("The end date must be greater than the start date.")
    if start_date is None:
        start_date = datetime.min
    if end_date is None:
        end_date = datetime.max
    return start_date, end_date
