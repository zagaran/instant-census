import csv

from mongolia.constants import ID_KEY
from mongolia.errors import DatabaseConflictError
import re
import xlrd
from pytz import all_timezones

from werkzeug import secure_filename

from backend.admin_portal.common_helpers import raise_400_error
from backend.incoming.new_user import new_user_via_admin_portal
from backend.outgoing.dispatcher import (send_user_reactivation_message,
    send_user_pause_message, send_paused_cohort_user_restart_message)
from conf.settings import DISABLE_USER_STATUS_CHANGE_MESSAGES
from constants.cohorts import CohortStatus, FORBIDDEN_CUSTOM_ATTRIBUTES, ALLOWED_USER_UPLOAD_ATTRIBUTES
from constants.exceptions import BadPhoneNumberError
from constants.users import Status
from database.backbone.cohorts import Cohort
from database.tracking.users import User, Users
from utils.formatters import phone_format
from utils.logging import log_error
from utils.time import now


def change_merge_field_name_for_actions(actions, previous_attribute_name, new_attribute_name):
    """
        This function iterates through actions and replaces any instances of merge fields of the
        previous attribute name with the new attribute name for set_attribute and send_message.
        For example, if we're editing an attribute name from "foo" to "bar", this would convert
        the text "Hello [[foo]]" to "Hello [[bar]]".

        This returns a boolean for whether or not a change has been made

        Conditionals and Questions are handled by getting those objects directly.
    """
    save = False
    for action in actions:
        # for set_attribute
        if (action["action_name"] == "set_attribute" and
            action["params"]["attribute_name"] == previous_attribute_name):
            # change attribute name
            action["params"]["attribute_name"] = new_attribute_name
            # set flag
            save = True
        # for send_message
        elif action["action_name"] == "send_message":
            # convert text
            previous_text = action["params"]["text"]
            processed_text = change_merge_field_name_for_text(previous_text, previous_attribute_name, new_attribute_name)
            # if differences in text
            if previous_text != processed_text:
                # change object text
                action["params"]["text"] = processed_text
                # set save flag
                save = True
    return save


def change_merge_field_name_for_text(text, previous_attribute_name, new_attribute_name):
    """
        This function processes text and replaces any instances of merge fields of the previous
        attribute name with the new attribute name.  For example, if we're editing an attribute
        name from "foo" to "bar", this would convert the text "Hello [[foo]]" to "Hello [[bar]]".
    """
    # set up regex
    regex_pattern = r"\[\[[ ]?" + re.escape(previous_attribute_name) + "[ ]?\]\]"  # the space is optional "[[thing]]"
    regex = re.compile(regex_pattern, re.IGNORECASE)  # ignore case
    # do regex and replace with uppered new attribute name
    return regex.sub("[[%s]]" % new_attribute_name.upper(), text)


def create_new_uploaded_attributes(custom_attributes, cohort):
    for attribute_name in custom_attributes:
        # TODO: refactor. Reason for the following two lines is timezone is top-level attribute, not custom attribute
        if attribute_name == "timezone":
            continue
        # if attribute not exist in custom attributes, create it
        if attribute_name and attribute_name not in cohort.get_custom_attributes():
            default_value = ""
            cohort.add_custom_attribute(attribute_name, default_value)
            for user in Users(cohort_id=cohort[ID_KEY]):
                user.add_custom_attribute(attribute_name, default_value)
    return Cohort(cohort[ID_KEY])


def format_headers(headers):
    return [h.lower().strip() for h in headers]


def  parse_uploaded_user_file(user_file, cohort, option="safe", delay=True):
    """
    :param option: "safe" or "unrestricted";
        if option == "safe", use all validation
        elif option == "unrestricted" allow modification of data (bypass existing user check)
    """
    curr_time = now()
    filename = secure_filename(user_file.filename)
    if filename.endswith(".csv"):
        # gets content from in-memory file
        user_file = user_file.read()
        # replace "/r" newline characters and filter out "" for correct csvreader parsing
        user_file = filter(None, user_file.replace("\r", "\n").split("\n"))
        user_csv_reader = csv.reader(user_file)
        headers = format_headers(user_csv_reader.next())
        # validation
        header_errors = validate_headers(headers, cohort)
        if header_errors:
            return header_errors
        custom_attributes = headers[1:]  # remove phone number
        errors = validate_contents(user_csv_reader, cohort[ID_KEY], custom_attributes, option)
        if errors:
            return errors
        # creation
        cohort = create_new_uploaded_attributes(custom_attributes, cohort)
        # create new csv.reader from file and skip headers
        user_csv_reader = csv.reader(user_file)
        user_csv_reader.next()
        for row in user_csv_reader:
            parse_user(row, cohort, custom_attributes, curr_time, delay)
    elif filename.endswith(".xls") or filename.endswith(".xlsx"):
        book = xlrd.open_workbook(file_contents=user_file.read())
        sheet = book.sheet_by_index(0)
        headers = format_headers(sheet.row_values(0))
        # validation
        header_errors = validate_headers(headers, cohort)
        if header_errors:
            return header_errors
        custom_attributes = headers[1:]  # remove phone number
        errors = validate_contents(sheet, cohort[ID_KEY], custom_attributes, option, xls=True)
        if errors:
            return errors
        # creation
        cohort = create_new_uploaded_attributes(custom_attributes, cohort)
        for row_number in range(1, sheet.nrows):
            row = sheet.row_values(row_number)
            parse_user(row, cohort, custom_attributes, curr_time, delay)
    else:
        return raise_400_error("Please upload an Excel or CSV file.")


def parse_user(row, cohort, custom_attributes, curr_time, delay):
    phonenumber = row[0]
    # the next two lines are necessary because excel represents phone numbers as floats
    if isinstance(phonenumber, float):
        phonenumber = str(int(phonenumber))
    # check if user exists
    phonenumber = phone_format(str(phonenumber))
    user = User.retrieve(phonenum=phonenumber, cohort_id=cohort[ID_KEY])
    if not user:
        user = new_user_via_admin_portal(phonenumber, cohort[ID_KEY], curr_time, delay=delay)
    # spreadsheet index is 1-indexed
    for column in range(1, len(custom_attributes) + 1):
        # dictionary is 0-indexed
        custom_attribute_name = custom_attributes[column - 1]
        # grab value for that column and row, else set as empty string
        row_value = row[column]
        # convert floats to int if is_integer() because xlsx will convert numerics to floats
        # NOTE: corner case where the admin intended for the value to actually be a float and this messes with that
        if isinstance(row_value, float):
            if row_value.is_integer():
                row_value = str(int(row_value))
            else:
                row_value = str(row_value)
        # if string, strip whitespace
        if isinstance(row_value, basestring):  # can't just do string casting since xlsx will convert ints to floats
            row_value = row_value.strip()
        custom_attribute_value = row_value if row_value != "" else ""
        if custom_attribute_name == "timezone":
            user["timezone"] = custom_attribute_value
        # set user attribute in customer attributes dictionary
        user["custom_attributes"][custom_attribute_name] = unicode(custom_attribute_value)
    user.save()


def send_status_message(user):
    if user.get_cohort()["status"] == CohortStatus.active and not DISABLE_USER_STATUS_CHANGE_MESSAGES:
        if user["status"] == Status.active:
            send_user_reactivation_message(user)
        elif user["status"] == Status.paused:
            send_user_pause_message(user)
        elif user["status"] == Status.disabled:
            pass  # let twilio handle it
    elif user.get_cohort()["status"] == CohortStatus.paused and user["status"] == Status.active:
        send_paused_cohort_user_restart_message(user)


def update_merge_fields_in_object(object, previous_attribute_name, new_attribute_name):
    """
        Updates attribute names for Question, Conditional, and Schedule objects given a previous_attribute_name
        and new_attribute_name.  Will only save if changes are made.
        Returns True if changes are made, False if changes are not.
    """
    # save flag to determine if database call to save is needed
    save = False
    # for objects with text
    if "text" in object:
        # change merge fields in text
        previous_text = object["text"]
        processed_text = change_merge_field_name_for_text(previous_text, previous_attribute_name, new_attribute_name)
        # if differences in text
        if previous_text != processed_text:
            # change object text
            object["text"] = processed_text
            # set save flag
            save = True
    # for objects with attribute
    if "attribute" in object:
        if object["attribute"] == previous_attribute_name:
            # change attribute name
            object["attribute"] = new_attribute_name
            # set save flag
            save = True
    # for objects with actions
    if "actions" in object:
        # change merge fields in actions
        actions = object["actions"]
        # this function will return True if changes have been made
        changed = change_merge_field_name_for_actions(actions, previous_attribute_name, new_attribute_name)
        # if differences, set save flag
        if changed:
            save = True
    # if save flag is True, save
    if save:
        object.save()
        return True
    else:
        return False


def validate_contents(user_file, cohort_id, custom_attributes, option, xls=False):
    errors = {
        "bad_phonenumbers": [],
        "existing_users": [],
        "unknown": [],
        "phone_number_repeats": [],
        "timezone_errors": [],
        "phonenum_list": {},  # Exists to check for repeated phone number in upload
    }
    # if xls (excel) file
    if xls:
        for index in range(1, user_file.nrows):
            row = user_file.row_values(index)
            row_number = index + 1
            errors = validate_row(row, row_number, cohort_id, custom_attributes, errors, option)
    # if csv file
    else:
        for row in user_file:
            row_number = user_file.line_num + 1
            errors = validate_row(row, row_number, cohort_id, custom_attributes, errors, option)
    errors.pop("phonenum_list")  # This isn't an error - just used to check for repeated phone numbers
    # if errors, return
    if any([True if value else False for key, value in errors.items()]):
        return errors


def validate_headers(headers, cohort):
    header_errors = {"headers": []}
    if headers[0].replace(" ", "") != "phonenumber":
        header_errors["headers"].append("'Phone Number' is a required first column header. As a consequence, note that user phone numbers belong in the first column.")
    for column in range(1, len(headers)):
        if headers[column] in FORBIDDEN_CUSTOM_ATTRIBUTES and headers[column] not in ALLOWED_USER_UPLOAD_ATTRIBUTES:
            error = "Attribute '%s' is not an allowed custom user attribute." % headers[column].upper()
            header_errors["headers"].append(error)
    if header_errors["headers"]:
        return header_errors


def validate_user_attribute(new_attribute_name, new_default_value, cohort,
                            previous_attribute_name=False, previous_default_value=False):
    """
        Validates creation or editing of user attributes. Will raise 400 error if problems and return
        True if no problems
    """
    # generic validation
    # disallow this action on completed cohorts
    if cohort["status"] == CohortStatus.completed:
        raise_400_error("This action is not allowed on a cohort that is already completed.", "error")
    # disallow periods in attribute name
    if "." in new_attribute_name:
        raise_400_error(("Sorry, periods '.' are not allowed in attribute names. Underscores are recommended " + 
                         "instead: '%s'") % new_attribute_name.replace(".", "_"), "error")
    if new_attribute_name[0] == "$":
        raise_400_error("Sorry, attribute names cannot begin with the character '$'.", "error")
    # disallow forbidden names for new attribute name
    if new_attribute_name in FORBIDDEN_CUSTOM_ATTRIBUTES:
        raise_400_error("The attribute '%s' already exists or is not allowed." % new_attribute_name.upper())

    # validation for new attribute
    if not previous_attribute_name and not previous_default_value:
        # disallow duplicate attribute names
        if new_attribute_name in cohort.get_custom_attributes():
            raise_400_error("The attribute '%s' already exists." % new_attribute_name.upper())

    # validation for edit attribute
    else:
        # these should never happen unless admin messed with js
        if previous_attribute_name not in cohort["custom_attributes"]:
            raise_400_error("The attribute '%s' does not exist for this cohort." % previous_attribute_name.upper(), "error")
        if previous_default_value != cohort["custom_attributes"][previous_attribute_name]:
            raise_400_error(("The default value '%s' for attribute '%s' is not valid for this cohort."
                             % (previous_default_value.upper(), previous_attribute_name.upper())), "error")
        # disallow editing to duplicate attribute name
        if (new_attribute_name != previous_attribute_name and
            new_attribute_name in cohort.get_custom_attributes()):
            raise_400_error(("The attribute '%s' cannot be renamed to '%s' because that attribute already " + 
                             "exists.") % (previous_attribute_name.upper(), new_attribute_name.upper()), "error")

    return True


def validate_row(row, row_number, cohort_id, custom_attributes, errors, option):
    """Validates: phonenumber is in first column, checks phonenumber format and existence and repeats """
    # Assumes phonenumber is first column header
    phonenumber = row[0]
    # check exists because excel files will tend to represent phone numbers as floats (appending on a ".0")
    if isinstance(phonenumber, float):
        if int(phonenumber) != phonenumber:
            errors["bad_phonenumbers"].append("%s (row %s)" % (phonenumber, row_number))
            return errors
        phonenumber = int(phonenumber)
    # Checks to see if uploaded phone number already exists in database
    try:
        phonenum = phone_format(str(phonenumber))
        if User.retrieve(phonenum=phonenum, cohort_id=cohort_id):
            raise DatabaseConflictError
    # if phone number is wrongly formatted
    except (BadPhoneNumberError):
        # if float, try to remove .0 in error messages
        errors["bad_phonenumbers"].append("%s (row %s)" % (phonenumber, row_number))
    except DatabaseConflictError:
        # if upload mode is unrestricted, allow editing to happen
        if option == "unrestricted":
            pass
        else:
            # if user exists and mode is safe upload, add to errors
            errors["existing_users"].append("%s (row %s)" % (phonenumber, row_number))
    # unknown error
    except Exception as e:
        log_error(e, "Parsing phonenumber in an uploaded user file caused unknown error.")
        errors["unknown"].append("%s (row %s)" % (phonenumber, row_number))
    else:
        # log phone number as seen
        if phonenumber not in errors["phonenum_list"]:
            errors["phonenum_list"][phonenumber] = row_number
        # phone number is repeated
        else:
            errors["phone_number_repeats"].append("%s (row %s, repeat found in row %s)" % 
                                                  (phonenumber, row_number, errors["phonenum_list"][phonenumber]))
    # check if timezone is valid
    if "timezone" in custom_attributes:
        # offset of 1 because phone number was popped
        user_timezone = row[custom_attributes.index("timezone") + 1]
        if user_timezone not in all_timezones:
            errors["timezone_errors"].append("%s (row %s)" % (user_timezone, row_number))
    return errors
