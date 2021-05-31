import traceback
import socket
from boto import ses
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from constants.messages import (ENG_EMAIL_CONTACT, EMAIL_FROM_ADDRESS, FULL_FROM_ADDRESS)

try:
    from conf.secure import SES_ACCESS_KEY_ID
    from conf.secure import SES_SECRET_ACCESS_KEY
except:
    SES_ACCESS_KEY_ID = ""
    SES_SECRET_ACCESS_KEY = ""
from constants.messages import (ENG_EMAIL_CONTACT, FULL_FROM_ADDRESS)


def send_eng_email(subject, body, convert_newlines=True):
    from_address = "%s <%s>" % (socket.gethostname(), ENG_EMAIL_CONTACT)
    to_address = ENG_EMAIL_CONTACT
    if convert_newlines:
        body = body.replace("\n", "<br>")
    __send_email(from_address, subject, body, to_address)

def send_email(to_address, subject, body):
    from_address = FULL_FROM_ADDRESS
    __send_email(from_address, subject, body, to_address)

def send_eng_html(subject, html_body):
    send_eng_email(subject, html_body, convert_newlines=False)

def send_html(to_address, subject, html_body):
    send_email(to_address, subject, html_body)

def __send_email(from_address, subject, body, to_address):
    try:
        conn = ses.connect_to_region(
            "us-east-1",
            aws_access_key_id=SES_ACCESS_KEY_ID,
            aws_secret_access_key=SES_SECRET_ACCESS_KEY
        )
        conn.send_email(from_address, subject, body, [to_address], format="html")
    except Exception as e:
        log_email_exception(e, from_address, to_address, subject, body)
        try:
            # Send email fallback
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = from_address
            message["To"] = to_address
            message.attach(MIMEText(body, "html"))
            server = smtplib.SMTP("localhost")
            server.sendmail(from_address, [to_address], message.as_string())
            # Notify engineering
            eng_message = MIMEMultipart("alternative")
            eng_message["Subject"] = "ERROR IN SES: %s" % subject
            eng_message["From"] = from_address
            eng_message["To"] = ENG_EMAIL_CONTACT
            body = ("To:<br>%s<br><br>From:<br>%s<br><br>Subject:<br>%s<br><br>Body:<br>%s"
                    % (to_address, from_address, subject, body))
            eng_message.attach(MIMEText(body, "html"))
            server.sendmail(from_address, [ENG_EMAIL_CONTACT], eng_message.as_string())
        except Exception as e:
            log_email_exception(e, from_address, to_address, subject, body)

def log_email_exception(e, from_address, to_address, subject, body):
    print("-------------------")
    print("Cannot send email:")
    print("    From: %s" % from_address)
    print("    To: %s" % to_address)
    print("    Subject: %s" % subject)
    print("    Body: %s" % body)
    print("Exception 1:")
    print(e)
    print("Traceback:")
    print(traceback.format_exc())
    print("-------------------")

