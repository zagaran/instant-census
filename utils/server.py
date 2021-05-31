from __future__ import division
from socket import gethostbyname, gethostname
from os import statvfs, listdir
from functools import wraps
from urlparse import urlparse

import requests
from twilio.rest import TwilioRestClient
from twilio import TwilioRestException
from httplib2 import ServerNotFoundError

from constants.exceptions import UnknownPhoneNumberError

from conf.secure import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_TEST_ACCOUNT_SID, TWILIO_TEST_AUTH_TOKEN

DISK_TEST_PATH = "temp.temp"
DEFAULT_PAGE_SIZE = 5000

PRODUCTION = sum(1 for i in listdir(".") if i.endswith(".wsgi"))
TEST_RUN = False

def development_only(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not PRODUCTION:
            return f(*args, **kwargs)
        else:
            print "WARNING: '%s' was not called because you are in a PRODUCTION environment.\n" % f
    return wrapped


def get_twilio_client():
    if PRODUCTION:
        return TwilioRestClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    else:
        # If in local development, use Twilio's test credentials
        return TwilioRestClient(TWILIO_TEST_ACCOUNT_SID, TWILIO_TEST_AUTH_TOKEN)


def get_twilio_client_testing():
    return TwilioRestClient(TWILIO_TEST_ACCOUNT_SID, TWILIO_TEST_AUTH_TOKEN)


class MyICNumbers(list):
    def reload(self):
        my_ip_addr = my_ip_address()
        try:
            twilio_client = get_twilio_client()
            numbers = [pn.phone_number for pn in twilio_client.phone_numbers.list(page_size=DEFAULT_PAGE_SIZE)
                       if ip_of_url(pn.sms_url) == my_ip_addr]
            list.__init__(self, numbers)
        except (TwilioRestException, ServerNotFoundError):
            if PRODUCTION:
                raise
            else:
                # print "WARNING: cannot connect to twilio for MyICNumbers"
                pass

    __init__ = reload


def ip_of_phonenum(phonenum):
    twilio_client = get_twilio_client()
    for pn in twilio_client.phone_numbers.list():
        if pn.phone_number == phonenum:
            return ip_of_url(pn.sms_url)
    raise UnknownPhoneNumberError(phonenum)


def hostname_of_server(addr):
    try:
        r = requests.post("https://" + addr + "/hostname")
        name = r.text
        if r.ok and len(name) < 100:
            return str(name)
        return "unknown"
    except requests.exceptions.ConnectionError:
        pass

def all_servers():
    twilio_client = get_twilio_client()
    servers = [domain_of_url(pn.sms_url) for pn in twilio_client.phone_numbers.list(page_size=DEFAULT_PAGE_SIZE)]
    return list(set(servers))


def domain_of_url(url):
    return urlparse(url).netloc

def ip_of_url(url):
    return gethostbyname(domain_of_url(url))

def my_ip_address():
    return gethostbyname(gethostname())


def get_server_status(server):
    """ Returns tuple (status, mongo_status) """
    try:
        r = requests.post('https://' + server + '/ping', timeout=30)
    except requests.exceptions.RequestException:
        try:
            r = requests.post('http://' + server + '/ping', timeout=30)
        except requests.exceptions.RequestException:
            return (0, False)
    status = r.status_code
    if not r.ok:
        return (status, False)
    mongo = (r.text == 'pong')
    return (status, mongo)


def disk_test(disk="/"):
    """ returns whether there is at least 10% available on the disk """
    fs_stat = statvfs(disk)
    return 1.0 * fs_stat.f_bavail / fs_stat.f_blocks >= 0.1
