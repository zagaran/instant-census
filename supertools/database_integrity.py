from database.backbone.cohorts import Cohorts, Customer, Cohort
from database.backbone.schedules import (Questions, ActionNode, Question,
    Conditional, Schedules, Conditionals)
from database.tracking.users import Users
from utils.database import DatabaseObject, DatabaseCollection, ID_KEY, CHILD_TEMPLATE
from utils.testing import MultifailureTest
from utils.actions import ActionConfig
from parsers.registry import PARSERS, Parser
from supertools.subclass_detector import all_children


def test_database_integrity():
    with MultifailureTest() as test:
        test_database_schemas(test)
        test_cohorts(test)
        test_action_config(test)
        test_parser_config(test)


def test_database_schemas(test):
    for Subclass in all_children(DatabaseObject):
        if Subclass.PATH == CHILD_TEMPLATE:
            continue
        defaults = Subclass.DEFAULTS
        defaults[ID_KEY] = None
        coll = DatabaseCollection(objtype=Subclass, read_only=True)
        for item in coll:
            for key in item:
                if key in ["custom_attributes"]:
                    for attribute in item[key]:
                        test.assertTrue(type(attribute) == unicode, "Attribute key %s is not in unicode." % attribute)
                        test.assertTrue(type(item[key][attribute]) == unicode, "Attribute value %s is not in unicode." % item[key][attribute])
                test.assertTrue(key in defaults, Subclass.__name__ + ": has extra key " + key)
            for key in defaults:
                test.assertTrue(key in item, Subclass.__name__ + ": missing key " + key)

def test_cohorts(test):
    for cohort in Cohorts():
        customer = Customer(cohort["customer_id"])
        test.assertTrue(customer, "cohort " + str(cohort[ID_KEY]) +
                        " attached to invalid customer " + str(cohort["customer_id"]))
    for user in Users():
        cohort = user.get_cohort()
        if user["ic_number"] is None:
            continue
        test.assertTrue(user["ic_number"] in cohort["ic_numbers"],
                        "user %s ic_number not in cohort %s ic_numbers" %
                         (user[ID_KEY], cohort[ID_KEY]))
    for Subclass in [Schedules, Conditionals, Questions]:
        for obj in Subclass():
            cohort_id = obj["cohort_id"]
            test.assertTrue(Cohort.exists(cohort_id),
                            "Cohort %s doesn't exist; %s id %s" % (cohort_id, Subclass.__name__, obj[ID_KEY]))

def test_action_config(test):
    for Subclass in [Schedules, Conditionals, Questions]:
        for obj in Subclass():
            parent_cohort_id = obj["cohort_id"]
            subclass_id = obj[ID_KEY]
            for action in obj["actions"]:
                check_action_config(action, test, parent_cohort_id, subclass_id)

def check_action_config(action, test, parent_cohort_id, subclass_id):
    action_name = action["action_name"]
    if action_name == "send_question":
        question = Question(action["params"]["database_id"])
        test.assertTrue(question,
            "Question '%s' doesn't exist in subclass id '%s'" % (action["params"]["database_id"], subclass_id))
        if question:
            test.assertEqual(question["cohort_id"], parent_cohort_id,
                ("Question '%s' with cohort id '%s' has different cohort id than parent (id: '%s', cohort_id: '%s')") \
                % (question[ID_KEY], question["cohort_id"], subclass_id, parent_cohort_id)
            )
    if action_name == "conditional":
        conditional = Conditional(action["params"]["database_id"])
        test.assertTrue(conditional,
            "Conditional '%s' doesn't exist in subclass id '%s'" % (action["params"]["database_id"], subclass_id))
        if conditional:
            test.assertEqual(conditional["cohort_id"], parent_cohort_id,
                ("Conditional '%s' with cohort_id '%s' has different cohort id than parent (id: '%s', cohort_id: '%s')") \
                % (conditional[ID_KEY], conditional["cohort_id"], subclass_id, parent_cohort_id)
            )
    ActionConfig.create_config(action_name, action["params"])

def test_parser_config(test):
    for question in Questions():
        parser = question["parser"]
        if parser == Parser.open_ended or parser is None:
            continue
        test.assertTrue(parser in PARSERS, "Bad parser %s" % parser)
