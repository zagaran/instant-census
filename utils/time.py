from __future__ import division, absolute_import

from datetime import datetime, time, timedelta  # @UnusedImport so imports work

from pytz import utc, timezone

from constants.cohorts import ResendSubtype
from utils.logging import log_warning


timezone_cache = {}
def get_timezone(tz_name):
    """ creating time zone objects is slightly expensive, so we cache them.
        The try-except catching a key error is faster than testing for the presence of the key
        in the case where we do have the time zone cached. """
    try:
        return timezone_cache[tz_name]
    except KeyError:
        timezone_cache[tz_name] = timezone(tz_name)
        return timezone_cache[tz_name]

ARTIFICIAL_TIME = None

def now():
    if ARTIFICIAL_TIME is None:
        return datetime.utcnow()
    return ARTIFICIAL_TIME


def set_now(new_now):
    from utils.server import PRODUCTION
    assert not PRODUCTION
    assert (isinstance(new_now, datetime) or new_now is None)
    global ARTIFICIAL_TIME
    ARTIFICIAL_TIME = new_now

def is_artifical_time():
    return ARTIFICIAL_TIME is not None

def convert_from_utc(utc_dt, new_tz_string):
    new_time_zone = get_timezone(new_tz_string)
    return utc.localize(utc_dt).astimezone(new_time_zone).replace(tzinfo=None)

def convert_to_utc(dt, current_tz_string):
    local_time_zone = get_timezone(current_tz_string)
    return local_time_zone.localize(dt).astimezone(utc).replace(tzinfo=None)

def zero_day(dt):
    # Returns the datetime.datetime of midnight on the given day
    return datetime.combine(dt.date(), time.min)


def today():
    # Returns the datetime.datetime of midnight today
    return zero_day(now())


def date_to_timestamp(date):
    # Converts a datetime.date object to an integer timestamp
    return time.mktime(date.timetuple())


def timestamp_to_datetime(ts):
    # Converts an integer timestamp to a datetime.datetime object
    return datetime.fromtimestamp(ts)


def military_time(hour, ampm):
    # Changes a 12-hour time into 24-hour time; ex. 1PM -> 13
    hour = int(hour)
    if ampm == "pm" and hour != 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    return hour


def fourDigitYear(year):
    # Changes a two-digit year into a four-digit year
    century = str(now().year)[0:2]
    if int(year) > now().year % 100:
        return str(int(century) - 1) + year
    else:
        return century + year


def is_int(s):
    # Function for determining if input is an integer
    try:
        int(s)
        return True
    except ValueError:
        return False


def total_seconds(td):
    # Converts a timedelta object into the total number of seconds
    seconds = (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10 ** 6) / 10 ** 6
    return seconds


def dob_to_age(dob):
    try:
        # 2 vs 4 digit year
        if len(dob) == 2:
            return now().year - datetime.strptime(dob, "%y").year
        elif len(dob) == 4:
            return now().year - datetime.strptime(dob, "%Y").year
    except ValueError:
        return None


def days_in_question_period(start_time, question_days_of_week):
    # isoweekday has Monday == 1 ... Sunday == 7
    # mod by 7 to get Sunday == 0
    start_day = start_time.isoweekday() % 7
    # Remove duplicate days of week and sort the list
    days_of_week = sorted(set(question_days_of_week))
    if not days_of_week:
        log_warning("question_days_of_week is empty")
        raise Exception("question_days_of_week is empty")
    # Find the first day of week in the list greater than the current
    # day of week and return the difference
    for day in days_of_week:
        if day > start_day:
            return day - start_day
    # Otherwise, start_day is beyond the last day in the list, so compute the
    # difference from the first day in the list, adding 7 for rollover
    return 7 + days_of_week[0] - start_day


def resend_times(curr_time, start_time, resend_hour, number_of_resends, resend_type, daily_limit=False):
    # Creates a list of resend times based on current start time and the
    # schedule's resend parameters
    # TODO: Write Tests
    resends = []
    if daily_limit:
        resend = start_time
        for x in range(5):
            resend += timedelta(days=number_of_resends)
            resends.append(resend)
    elif resend_type == ResendSubtype.time:
        for x in range(int(number_of_resends)):
            resend = start_time
            resend = resend.replace(hour=resend_hour)
            if start_time.hour > resend_hour:
                resend += timedelta(days=x + 1)
            else:
                resend += timedelta(days=x)
            resends.append(resend)
    elif resend_type == ResendSubtype.hours:
        resend = start_time
        for x in range(int(number_of_resends)):
            resend += timedelta(hours=resend_hour)
            resends.append(resend)
    # Filter out resend times that have already passed
    return [time for time in resends if time >= curr_time]
