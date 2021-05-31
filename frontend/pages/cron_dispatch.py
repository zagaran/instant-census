from flask import Blueprint
from multiprocessing.process import Process
from backend.incoming.entry_points import every_hour
from database.analytics.system_load import EveryHourOTP
from requests import post
from socket import gethostname

cron_dispatch = Blueprint("cron_dispatch", __name__)


def start_every_hour():
    """ This is the function that should be called by cron directly.
        
        This function makes a post request to dispatch_every hour.  This is
        so that the every hour job runs with the same concurrency variables
        as on_receive.  To prevent extraneous and malicious calls to every_hour,
        a one time password is used. """
    password = EveryHourOTP.generate_password()
    # TODO: switch to https in production when servers have wildcard certificate
    resp = post("https://%s/dispatch_every_hour/%s" % (gethostname(), password))
    resp.raise_for_status()

@cron_dispatch.route("/dispatch_every_hour/<one_time_password>", methods=["POST"])
def dispatch_every_hour(one_time_password):
    """ This is the receiving point of start_every_hour's post request.  It
        checks that the one time password is correct and then dispatches
        every_hour. """
    EveryHourOTP.check_password(one_time_password)
    Process(target=every_hour).start()
    return "success"
