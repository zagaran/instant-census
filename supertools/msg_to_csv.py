# should be Access Code, Date, Time, Question_ID, Message Text, Message Value
from database.tracking.users import User, Users
import csv
def to_csv():
    path = "tracking.users"
    active = Users.active()
    file = open("txts.csv","a+")
    writer = csv.writer(file)
    for user in active:
        for message in user.messages():
            try:
                if message["incoming"]:
                    accesscode = str(user["access_code"])
                    date = message["time"].date()
                    times = message["time"].time()
                    text = str(message["text"])
                    number = str(user["cohort_id"])
                    questionID = str(message["question_id"])
                    try:
                        if (message["parsing"][0][2] == "yes_or_no_parser" or "number_parser"):
                            parsed = str(message["parsing"][0][1])
                            writer.writerow([date, times, text, number, questionID, accesscode, parsed])
                        break
                    except (KeyError, TypeError, IndexError): pass
                    writer.writerow([date, times, text, number, questionID, accesscode])
            except UnicodeEncodeError: pass
to_csv()
