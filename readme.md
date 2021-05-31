# Instant Census

Instant Census is a text message survey platform built by Zagaran, Inc.

# Deprecation Notice

As of 2021, this system depends on deprecated technology, and as a result, is no longer production suitable without substantial upgrades.  In particular:

* The backend is built on Python 2, which reached end of life in 2020
* The frontend is built with Angular 1, which reached end of life in 2021
* Instant Census was architected to give each customer its own set of phone numbers to prevent the problems that arise with shared short code use.  In order to do so cost effectively, Instant Census depends on using long-codes for texting, leveraging a technique called "snowshoeing" to prevent phone carriers from marking its legitimate SMS messages as spam.  As of 2021 phone carriers no longer allow snowshoeing, requiring all high-volume messaging to be done via short code which isn't compatible.

# Project Setup

* `pip install -r requirements.txt`
* `touch conf/settings_override.py`
* Copy `conf/secure.py.example` to `conf/secure.py` and fill in values
* Install mongodb and cronic (part of moreuitls)
* Run `app.py` or add a wsgi file with `from app import app as application`
* Add the following cron config:

```
# m h  dom mon dow   command
*/5 * * * * : five_minutes; cd <PROJECT_PATH>; chronic python cron.py five_minutes
0 */1 * * * : hourly; cd <PROJECT_PATH>; chronic python cron.py hourly
30 */4 * * * : four_hourly; cd <PROJECT_PATH>; chronic python cron.py four_hourly
@daily : daily; cd <PROJECT_PATH>; chronic python cron.py daily
0 2 * * 0 : weekly; cd <PROJECT_PATH>; chronic python cron.py weekly
@monthly : monthly; cd <PROJECT_PATH>; chronic python cron.py monthly
```

# Features

## Survey Features

* **One-Time Surveys:** Schedule surveys in advance to send at a pre-set date and time.
* **Recurring Surveys:**  Automatically send the same survey out on a recurring basis. (ex. Set a survey to send every Monday at 6pm.)
* **On-Creation Surveys:** Send surveys when recipients are onboarded.
* **Time Zone Support:** Surveys can send at a respondent's local time (if different time zones are set for different participants).
* **Skip Logic:** You can set which questions (or whole blocks of questions) a recipient will see, based either on the recipient's answers to previous survey questions, or based on custom fields that you set on the recipient ahead of time.
* **Piping:** Instant Census can pipe a recipient's answer into the text of any question later in that survey or in a future survey.
* **Merge Fields:** You can use merge fields in questions and outgoing messages. For example, you can send a message saying "Are you registered to vote in [[STATE]]?" where [[STATE]] is a custom field populated with the name of the state where the recipient lives.

## Question Types

* **Open Response Questions:** Instant Census supports open response questions that will accept any answer. Information given in open response answers can be piped into later survey questions.
* **Multiple Choice Questions:** The technology behind Instant Census allows the platform to intelligently parse responses so that respondents can answer survey questions naturally. For example, Instant Census would ask, "Are you female or male?" instead of "Are you female or male? Please respond 1 for female; 2 for male."
* **Numeric Range Questions:** Numeric questions ask the respondent to text back a number. You can set a range of acceptable answers.
* **Yes or No Questions:** Instant Census can ask questions that are looking for a response of "Yes" or "No", and will intelligently accept synonyms that are commonly used in texting. For example, "Yup" would be accepted and automatically coded as a "Yes" answer.
* **Messages:** Instant Census can also send messages that do not expect any response. These can be useful for sending notifications, alerts, and reminders.

## Data

* **Data Dashboard (Graphs, Reports):** The Instant Census Admin Portal shows graphs for data visualization. Researchers can see graphs in real time of answers, recipient custom fields, response rates, and response times.
* **CSV Data Export:** Dump all data into a CSV file, or you can selectively create a CSV file with certain data.
* **CSV/Excel Data Import:** Import study recipients and data into the system by uploading a CSV or XLX file.

## Recipient Management

* **Manage Recipient Profiles:** The Instant Census Admin Portal allows you to view recipients' information and edit the data stored in their custom fields. Each Cohort has its own recipient management page.
* **Automatic Opt-Out Handling:** Any recipient who texts STOP will be automatically opted out and will no longer receive messages from you unless they re-enable by texting START. You can view reports of opt-outs and see the conversation threads that led to people opting out.
* **Message Inbox:** When a recipient sends a message that Instant Census does not expect, the message is flagged and appears in the Message Inbox in the Instant Census Admin Portal. Here you can review the recipient's flagged message and follow up as appropriate.
* **View Recipient Conversation Transcripts:** The Message Inbox also allows you to view each individual recipient's message history. This is important if follow-up with an individual recipient is necessary.
* **Individual Message Sender:** Also within the Message Inbox, you can individually send messages to recipients from the Message Sender. For example, if a respondent is confused about a particular question, you can easily respond individually to each question without any interruption to the survey flow.
* **Custom Fields:** Custom fields are the primary way surveys can be tailored to a particular recipients. Every recipient in a particular Cohort has the same set of Custom Fields, but each recipient may have different values for those fields. Furthermore, each Custom Field has a default value set at time of creation which serves as the field value for any recipient on the Cohort who has not had the field explicitly set. These values can then be checked and set by surveys to guide the course of communication.
* **Pause/Unpause Recipients:** Each recipient has a status to indicate whether or not a recipient is actively receiving messages from Instant Census. This is shown in the third column of the recipients table.
* **Choose Your Area Code:** If you're distributing a survey to a group of recipients in a certain geographic location, you have the option to choose an area code from that specific location for your survey's phone number. For example, if you're distributing a survey to recipients in Boston, you could choose to use a 617 area code for your survey's phone number.

## Project Management

* **Cohorts:** Our platform groups together survey recipients and their associated surveys and schedules as an Instant Census Cohort, which can be thought of as projects. This allows you to group together people to whom you want to send the same surveys to easily organize and coordinate your studies and results.
* **Cohort Status Options:** Cohorts conveniently have statuses that provide you greater control over your studies. Active and paused statuses indicate whether or not a Cohort is actively sending out surveys, and a completed status allows you to stop all incoming and outgoing messages while retaining all associated data for archive.

