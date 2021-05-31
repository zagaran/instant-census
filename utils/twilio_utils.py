from conf.settings import COHORT_USER_LIMIT
from constants.users import TEST_USER_PHONENUM, Status
from socket import gethostname
from twilio import TwilioRestException
from twilio.rest.resources.phone_numbers import PhoneNumber  # , AvailablePhoneNumber
from constants.messages import TWILIO_MESSAGE_LENGTH
from constants.area_code_mapping import area_code_mapping
from utils.server import get_twilio_client, PRODUCTION, TEST_RUN
from utils.server import MyICNumbers
from utils.time import is_artifical_time, now, set_now, timedelta
from utils.logging import log_warning, log_error
from constants.exceptions import (PhoneNumberPurchaseException,
    PhoneSearchException, BadPhoneNumberError, TwilioDeliveryException)


MY_IC_NUMBERS = MyICNumbers()
TWILIO_CLIENT = get_twilio_client()
SMS_FALLBACK_URL = "https://stable.instantcensus.com/twilio/alert"
VOICE_URL = "https://stable.instantcensus.com/reject_call"
TWILIO_TEST_FROM_PHONENUM_VALID = "+15005550006"

# see https://www.twilio.com/docs/errors/reference
TWILIO_BLACKLIST_CODE = 21610
TWILIO_INVALID_FROM_NUMBER_CODE = 21606

# MESSAGE DELIVERY CODES
# TWILIO_QUEUE_OVERFLOW = 30001
# TWILIO_ACCOUNT_SUSPENDED = 30002
# TWILIO_UNREACHABLE_DESTINATION_HANDSET = 30003
# TWILIO_MESSAGE_BLOCKED = 30004
TWILIO_UNKNOWN_DESTINATION_HANDSET = 30005
TWILIO_LANDLINE_OR_UNREACHABLE_CARRIER = 30006
# TWILIO_CARRIER_VIOLATION = 30007
# TWILIO_UNKNOWN_ERROR = 30008
# TWILIO_MISSING_SEGMENT = 30009

def twilio_send(user, message_body):
    #############################################################################
    # Note: because TWILIO_MESSAGE_LENGTH is 1600, recursive call disabled to prevent sending absurdly long messages
    # if len(message_body) > TWILIO_MESSAGE_LENGTH:
    #     twilio_send(user, message_body[:TWILIO_MESSAGE_LENGTH])
    #     twilio_send(user, message_body[TWILIO_MESSAGE_LENGTH:])
    #     return
    #
    # if not PRODUCTION:
    #     return send_failure("Attempt to send sms from non-production instance.", user, message_body)
    ##############################################################################
    # if PRODUCTION, check user's ic_number and include a callback url
    if PRODUCTION and not TEST_RUN:
        if user["phonenum"] == TEST_USER_PHONENUM:
            return send_failure("Attempted to send to test user phone number", user, message_body)
        if user["ic_number"] is None:
            if COHORT_USER_LIMIT:
                log_warning("A outgoing messsage %s was not sent to user %s due to " +
                            "its cohort '%s' being over its user limit" % (
                                message_body, user["phonenum"], user["cohort_id"]))
            else:
                log_error("A user %s in cohort '%s' was found without an IC number. Message: %s" % (
                            user["phonenum"], user["cohort_id"], message_body))
        if user["ic_number"] not in MY_IC_NUMBERS:
            MY_IC_NUMBERS.reload()
            if not MY_IC_NUMBERS:
                return send_failure("No valid ICNumbers.", user, message_body)
            if user["ic_number"] not in MY_IC_NUMBERS:
                return send_failure("The ICNumber %s is not usable." % (user["ic_number"]),
                                    user, message_body)
        from_phonenum = user["ic_number"]
        callback_url = "https://%s/twilio/callback" % gethostname()
    # else, in local development, use Twilio's special test phone number without callback url
    else:
        from_phonenum = TWILIO_TEST_FROM_PHONENUM_VALID
        callback_url = ""  # TODO: Graceful handling of twilio callbacks that won't overload workers
    try:
        return TWILIO_CLIENT.messages.create(
            to=user["phonenum"],
            from_=from_phonenum,
            body=message_body,
            # status_callback=callback_url
        )
    # catch specific Twilio exceptions so we can handle them specifically
    except TwilioRestException as e:
        # exception if user has texted 'STOP'
        if e.code == TWILIO_BLACKLIST_CODE:
            log_warning("Blacklisted message '%s' send attempted to %s from %s" % (message_body, user["phonenum"], user["ic_number"]))
            user.set_status(Status.disabled)
            raise TwilioDeliveryException
        # exception if IC number is invalid
        elif e.code == TWILIO_INVALID_FROM_NUMBER_CODE:
            log_error(e, "Unable to send text message '%s' to %s from %s due to invalid IC number." % (message_body, user["phonenum"], user["ic_number"]))
            raise TwilioDeliveryException
        elif e.code in [TWILIO_UNKNOWN_DESTINATION_HANDSET, TWILIO_LANDLINE_OR_UNREACHABLE_CARRIER]:
            log_error(e, "Unable to send text message '%s' to %s from %s due to user number determined as unknown, landline, or unreachable." % (message_body, user["phonenum"], user["ic_number"]))
            user.set_status(Status.disabled)
            user["phonenum_status"] = "Landline/Unknown Number"
            user.save()
            raise TwilioDeliveryException
        else:
            raise e


def send_failure(error, user, message_body):
    if is_artifical_time():
        assert not PRODUCTION
        set_now(now() + timedelta(minutes=1))
    log_warning("%s\nfrom: %s\nto: %s\nmsg: %s" %
          (error, user["ic_number"], user["phonenum"], message_body))


def create_new_phonenum(friendly_name, area_code=None):
    """ Careful. This method attempts to make a Twilio purchase """
    if area_code:
        area_code = str(area_code) + "*******"
        new_phonenum = purchase_number_in_same_area_code(area_code)
        # if purchasing by area code fails, try purchasing random number
        if not new_phonenum:
            new_phonenum = purchase_random_number()
    else:
        new_phonenum = purchase_random_number()
    sms_url = "https://%s/sms_in" % gethostname()
    new_phonenum.update(sms_url=sms_url, sms_fallback_url=SMS_FALLBACK_URL, voice_url=VOICE_URL,
                        friendly_name=friendly_name)
    # Returns "+1XXXXXXXXXX" field of Twilio.PhoneNumber object
    return new_phonenum.phone_number

def release_phonenumbers(ic_number_list):
    """ This releases Twilio phone numbers in wild."""
    for phonenum in TWILIO_CLIENT.phone_numbers.list():
        if phonenum.phone_number in ic_number_list:
            TWILIO_CLIENT.phone_numbers.delete(phonenum.sid)

def serve_twilio_response(message="", reject=False):
    xml = '<?xml version="1.0" encoding="UTF-8" ?><Response>'
    if message:
        xml += message
    if reject:
        xml += '<Reject />'
    xml += '</Response>'
    return xml

################################################################################
############################## Purchasing ######################################
################################################################################

def _purchase(unpurchased_number):
    """ Takes a get_twilio_client AvailablePhoneNumber object and attempts to purchase it.
        Returns a string of the phone number in the form +1XXXXXXXXXX if the
        purchase was successful.
        Raises PhoneNumberPurchaseExceptions if the number cannot be purchased."""
    # Buying is literally AvailablePhoneNumber.purchase().
    # There is apparently a way to call the API to purchase directly based on an
    # by area code.  I cannot find it.
    # purchase() returns False if the new_purchase fails, a PhoneNumber on success.
    try:
        new_purchase = unpurchased_number.purchase()
    except:
        raise
    if isinstance(new_purchase, PhoneNumber):
        return new_purchase  # This returns a Twilio.PhoneNumber object
    if new_purchase == False:  # we actually do want to make sure it is == False...
        raise PhoneNumberPurchaseException("Phone number purchase failed.")
    raise Exception("Unknown error: new_purchase was neither bool nor PhoneNumber")

# def purchase_number(phone_number):
#     """ Purchases the number corresponding to the string entered, or if the
#         string is less than 10 digits it purchases the first match of that prefix."""
#     unpurchased_numbers = search_string(phone_number)
#     first_number = unpurchased_numbers[0]
#     return _purchase(first_number)
#
# def purchase_number_in_same_state(phone_number):
#     """ Takes a string of a phone number and purchases a number from the same state."""
#     unpurchased_numbers = search_by_state(phone_number)
#     first_number = unpurchased_numbers[0]
#     return _purchase(first_number)

def purchase_number_in_same_area_code(phone_number):
    """ Takes a string of a phone number and purchases a number in the same area code."""
    unpurchased_numbers = search_by_area_code(phone_number)
    for i in range(4):
        first_number = unpurchased_numbers[i]
        try:
            pn = _purchase(first_number)
            return pn
        except:
            continue

def purchase_random_number():
    """ Purchases some random phone number."""
    unpurchased_numbers = search_string("")
    for i in range(4):
        first_number = unpurchased_numbers[i]
        try:
            pn = _purchase(first_number)
            return pn
        except:
            continue


################################################################################
################################ Searching #####################################
################################################################################
""" Searching: these are valid keywords for use in TWILIO_CLIENT.phone_numbers.search().
    type: valid values are "local", "tollfree", and "mobile".
    region: takes a state abbreviation, returns only phone numbers local to that state.
    postal_code: takes a zip code and returns numbers valid in that zip code.
    contains: a letter or number string, using * as the wildcard character.
    near_lat_long: (as a tuple) Find close numbers within Distance miles.
        distance: (integer) used with near_lat_long keyword.
    rate_center: don't care.
    country: don't care. """


def _handle_phone_search(search_list):
    if len(search_list) == 0:
        raise PhoneSearchException("No phone number matches found.")
    return search_list

def search_string(string):
    return _handle_phone_search(TWILIO_CLIENT.phone_numbers.search(contains=string))

def search_by_state(phone_number):
    """Matches area code to get the state of origin of a number, returns numbers
         from that state."""
    state = determine_us_state(grab_area_code(phone_number))
    return _handle_phone_search(TWILIO_CLIENT.phone_numbers.search(region=state))

def search_by_area_code(phone_number):
    """ determines the area code and searches for matches."""
    area_code_match = padded_area_code(phone_number)
    return _handle_phone_search(TWILIO_CLIENT.phone_numbers.search(contains=area_code_match))

################################################################################
########################### String Manipulation ################################
################################################################################


def padded_area_code(phone_number):
    """ Grabs an area code with proper behavior when output is dropped into
        get_twilio_client's search. """
    area_code = grab_area_code(phone_number)
    return area_code + "*******"

def grab_area_code(phone_number):
    """ Returns the area code of a number followed by *s to the end of a 10 digit
        number. """
    #number of form +1 XXX XXX XXXX (this should be the form get_twilio_client provides)
    if "+1" == phone_number[:2]:
        return phone_number[2:5]
    # number of form 1 XXX XXX XXXX
    if len(phone_number) == 11 and phone_number[0] == '1':
        return phone_number[1:4]
    # number of form XXX XXX XXXX
    if len(phone_number) == 10:
        return phone_number[:3]
    raise BadPhoneNumberError('"%s" is an invalid phone number.' % phone_number)


def determine_us_state(area_code):
    """ Returns 2 letter state abbreviation if it finds a matching area code,
        otherwise returns None."""
    if not isinstance(area_code, str):
        area_code = str(area_code)
    if area_code in area_code_mapping:
        return area_code_mapping[area_code][0]

def get_time_zone_offset(area_code):
    """ Returns an integer offset value if it finds a matching area code,
        otherwise returns None."""
    if not isinstance(area_code, str):
        area_code = str(area_code)
    if area_code in area_code_mapping:
        return area_code_mapping[area_code][1]
