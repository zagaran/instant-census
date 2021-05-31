#!/usr/bin/python
######################################################################
# import utils.database  # @UnusedImport to ensure database connection
######################################################################


from __future__ import division

from sys import argv

from cronutils import run_tasks, ErrorSentry
from cronutils.error_handler import NullErrorHandler
from raven.exceptions import InvalidDsn
from raven.transport import HTTPTransport
from conf.secure import SENTRY_DSN

def run_cron():
    from backend.analytics.status_counts import store_status_counts
    from backend.analytics.users_and_messages import send_billing_report_by_cohort
    from frontend.pages.cron_dispatch import start_every_hour
    from supertools.database_integrity import test_database_integrity
    from supertools.server import email_server_summary, email_disk_alerts
    from utils.database import do_backup
    
    FIVE_MINUTES = "five_minutes"
    HOURLY = "hourly"
    FOUR_HOURLY = "four_hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    
    TASKS = {
        FIVE_MINUTES: [email_server_summary],
        HOURLY: [start_every_hour, email_disk_alerts],
        FOUR_HOURLY: [test_database_integrity],
        DAILY: [store_status_counts, do_backup],
        WEEKLY: [],
        MONTHLY: [send_billing_report_by_cohort],
    }
    
    TIME_LIMITS = {
        FIVE_MINUTES: 180,  # 3 minutes
        HOURLY: 3600,       # 60 minutes
        FOUR_HOURLY: 5400,  # 1.5 hours
        DAILY: 43200,       # 12 hours
        WEEKLY: 86400,      # 1 day
        MONTHLY: 86400,     # 1 day
    }
    
    VALID_ARGS = [FIVE_MINUTES, HOURLY, FOUR_HOURLY, DAILY, WEEKLY, MONTHLY]

    if len(argv) <= 1:
        raise Exception("Not enough arguments to cron\n")
    elif argv[1] in VALID_ARGS:
        cron_type = argv[1]
        run_tasks(TASKS[cron_type], TIME_LIMITS[cron_type], cron_type)
    else:
        raise Exception("Invalid argument to cron\n")

if __name__ == "__main__":
    try:
        error_handler = ErrorSentry(SENTRY_DSN, sentry_client_kwargs={'transport': HTTPTransport})
    except InvalidDsn:
        error_handler = NullErrorHandler()
        print "\nThe sentry DSN provided, '%s', is not valid. Running without sentry.\n" % SENTRY_DSN
    
    with error_handler:
        run_cron()

    # when running with Sentry want to forcibly exit 0 because we do not want cron emails.
    if isinstance(error_handler, ErrorSentry):
        exit(0)
