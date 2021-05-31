#!usr/bin/python

import app
import cron
from constants.database import CHILD_TEMPLATE
from constants.messages import ENG_EMAIL_CONTACT
from backend.database import DatabaseDict
from backend.database import DatabaseCollection
import json
from supertools.subclass_detector import all_collections
#from utils.email_utils import send_eng_html

"""
detects whether document count in collections goes down
hook up to crontab, put into supertools
author contact: kfan
"""

OUTFILE = "collections_count.txt"

EMAIL_FROM_ADDRESS = "info@zagaran.com"

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib, socket
def __send_email(toaddr, message):
    try:
        server = smtplib.SMTP("localhost")
        server.sendmail(EMAIL_FROM_ADDRESS, [toaddr], message)
    except socket.error as e:
        print(e.__repr__(), "Cannot send message: " + str(message))

def send_eng_html(subj, html_body):
    toaddr = ENG_EMAIL_CONTACT
    message = MIMEMultipart('alternative')
    message['Subject'] = subj
    message['From'] = str(socket.gethostname()) + "<" + ENG_EMAIL_CONTACT + ">"
    message['To'] = toaddr
    message.attach(MIMEText(html_body, 'html'))
    __send_email(toaddr, message.as_string())


def main():
    #load old counts from txt outfile
    try:
        with open(OUTFILE, "r") as outfile:
            old_counts = json.load(outfile)
    except:
            old_counts = {}
            subj = "Exception raised: collections outfile "
            body = "JSON dumping collections outfile on server raised an exception"
            send_eng_html(subj, body)
    new_counts = {}
    data_loss = []

    for collection in all_collections():
        name_key = collection.__objtype__.__db__
        new_count = collection.count()
        new_counts[name_key] = new_count

        if name_key in old_counts:
            old_count = old_counts[name_key]
            if new_count < old_count:
                data_loss.append((name_key, old_count, new_count))
 
    if data_loss:
        subj = "ALERT! SERVER DATA LOSS"
        for (a,b,c) in data_loss:
            body += "<p>Collection %s had count %s and now has count %s </p>" % (str(a),str(b),str(c))
        send_eng_html(subj, body)
    with open(OUTFILE, "r+") as outfile:
        outfile.truncate() #wipe file
        json.dump(new_counts, outfile)

if __name__ == '__main__':
    main()
