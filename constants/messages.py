from conf.settings import MONTHLY_MSG_USAGE_LIMIT

TWILIO_MESSAGE_LENGTH = 1600
SMS_LENGTH = 160

ENG_EMAIL_CONTACT = "eng@instantcensus.com"
EMAIL_FROM_ADDRESS = "support@instantcensus.com"
FULL_FROM_ADDRESS = "Instant Census <%s>" % EMAIL_FROM_ADDRESS


BAD_ACCESS_CODE = "Invalid access code. Please make sure you have entered it correctly."

CRISIS = ("Need help? In the U.S., call 1-800-273-8255 to reach the National " +
          "Suicide Prevention Lifeline.")

STOP_WORD_IN_MESSAGE = ("You sent us a message with the word '%s' in it. If you " +
                        "would like to stop receiving messages, text the word 'STOP'. Otherwise, text 'OK'.")

DEFAULT_WAITLIST = ("Welcome! Thank you for your interest. Your number has been " +
                    "added to the waitlist.")

DEFAULT_USER_RESTART = ("Welcome back! Your number has been reactivated in our " +
                        "system and will begin receiving messages from us again. " +
                        "Text 'STOP' to end messages at any time.")
DEFAULT_USER_PAUSE = ("Your number has been deactivated in our system and will " +
                      "not receive messages from us until it has been reactivated.")

DEFAULT_COHORT_RESTART = ("We're back! We have resumed sending messages, so you " +
                          "will begin receiving messages from us again. " +
                          "Text 'STOP' to end messages at any time.")
DEFAULT_COHORT_PAUSE = ("We are taking a short break from sending messages, so you " +
                        "will not receive messages from us until we are back.")

DEFAULT_PAUSED_COHORT_USER_RESTART = ("Welcome back! Your number has been " +
                                      "reactivated in our system, but we are not " +
                                      "currently sending messages at this time. We " +
                                      "will notify you when we resume.")

DEFAULT_WELCOME_CUSTOMIZABLE = "Welcome to Instant Census."
LEGALLY_REQUIRED = " Text 'STOP' to end messages at any time. Standard msg&data rates may apply."

DEFAULT_WELCOME = (DEFAULT_WELCOME_CUSTOMIZABLE + LEGALLY_REQUIRED)


WAITLIST_PROMOTION = ("Welcome! You have been moved off of the waitlist and your " +
                      "number has been activated in our system. You will now " +
                      "begin receiving messages from us.")

INACTIVE = ("You haven't responded to a question in a while, so we won't send you " +
            "any more questions. If you would like to reactivate, text us 'START'.")

PASSWORD_STRING = ("PASSWORD")
PASSWORD = ("Your temporary password is " + PASSWORD_STRING + ". It expires in 5 hours.")

DEFAULT_PENDING = DEFAULT_WAITLIST

RE_PING_PREPEND = "Haven't heard from you yet."

MULTIPLE_CHOICE_RESEND_TEXT = "Please enter response text exactly."

OVER_USAGE_LIMIT_MESSAGE = ("You are over your monthly message limit of %s messages. " +
                            "Your messages are no longer being sent. Please contact " +
                            "support@instantcensus.com if you wish to increase your " +
                            "capacity.") % MONTHLY_MSG_USAGE_LIMIT
