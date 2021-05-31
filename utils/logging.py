import socket
import traceback
from datetime import datetime

from cronutils import ErrorSentry
from raven.exceptions import InvalidDsn
from raven.transport import HTTPTransport

from conf.secure import SENTRY_DSN
from utils.email_utils import send_eng_email
from utils.server import PRODUCTION


def log_error(e, message=None, time=False, email=True):
    try:
        tb = traceback.format_exc()
        print("-------------------")
        if message is not None:
            print(message)
        if time:
            print("%s ERROR: %s" % (datetime.utcnow(), e.__repr__()))
        else:
            print("ERROR: %s" % (e.__repr__()))
        print(tb)
        print("-------------------")
        if PRODUCTION and email:
            body = ("%s\r\n\r\n%s\r\n\r\nMessage: %s" %
                    (e.__repr__(), tb.replace("\n", "\r\n"), message))
            send_eng_email("ERROR: %s" % (socket.gethostname()), body)
    except Exception as e:
        print("ERROR IN log_error")
        print(e)

def log_warning(message, email=True):
    try:
        print("-------------------")
        print("WARNING: %s" % (message))
        print("-------------------")
        if PRODUCTION and email:
            send_eng_email("WARNING: %s" % (socket.gethostname()),
                          "WARNING: %s" % (message))
    except Exception as e:
        print("ERROR IN log_warning")
        print(e)


def log_thread(f):
    """ Wrapper function for email logging of thread-functions.
        WARNING: this wrapper swallows any error (to prevent double logging),
        so don't use it on functions that need exceptions passed up """
    def wrapped(*args, **kwargs):
        try:
            with ErrorSentry(SENTRY_DSN, sentry_client_kwargs={'transport': HTTPTransport}):
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    # TODO: consider making a global setting to enable emails in addition to sentry.
                    # TODO: change email value once sentry configuration is finalized.
                    log_error(e, time=False, email=True)
                    raise
        
        except InvalidDsn:
            try:
                return f(*args, **kwargs)
            except Exception as e:
                log_error(e, time=True)
    
    return wrapped
