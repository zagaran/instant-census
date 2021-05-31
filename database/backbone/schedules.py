from mongolia.constants import REQUIRED_STRING

from parsers.registry import Parser
from utils.database import DatabaseObject, DatabaseCollection, REQUIRED, ID_KEY, CHILD_TEMPLATE
from utils.actions import ActionConfig
from utils.logging import log_warning
from utils.time import now
from constants.cohorts import ConditionalSubtype, ResendSubtype

import uuid

class ActionNode(DatabaseObject):
    PATH = CHILD_TEMPLATE
    DEFAULTS = {"actions": []}
    
    def add_action(self, action_name, params_dict):
        action = ActionConfig.create_config(action_name, params_dict)
        self["actions"].append(action)
        self.save()
    
    def do_actions(self, user, parser_return=None, execution_state=[],
                   resend=False, delay=True):
        """ An execution state allows resuming the paused execution of an
            action tree.  It is a list of the form:
            [schedule_id, action_id, action_id, action_id, ..., question_id]
            There is always a question_id at the end because we only pause
            after asking a question. """
        # The first item of the execution state (if any) refers to self; strip it
        execution_state = execution_state[1:]
        current_action = None
        if execution_state:
            current_action = execution_state[0]
        for action in self["actions"]:
            if current_action and action["action_id"] != current_action:
                # If there is an execution_state we are working off of,
                # skip actions until the execution state is reached
                continue
            elif current_action and action["action_id"] == current_action:
                # resume doing current action
                ret = ActionConfig.do_action(
                    action, user, parser_return=parser_return,
                    execution_state=execution_state, resend=resend, delay=delay
                )
                # reset parser_return and mark current_action as done by setting it to None
                # TODO: bug introduced by setting parser_return to None if there exists multiple conditionals on the same level
                # looking for that parser return, such as in numerical ranges
                parser_return = None
                current_action = None
            else:  # There is no current_action
                ret = ActionConfig.do_action(
                    action, user, parser_return=parser_return, delay=delay
                )
            if ret:
                ret.insert(0, self[ID_KEY])
                return ret
        if current_action:
            log_warning("Action %s not found in %s" % (current_action, self))
        return None
    
    def recursive_copy(self, cohort_id):
        #override cohort id during the copy otherwise schedule_executions get created for the wrong cohort
        copy = self.copy(attribute_overrides={"cohort_id": cohort_id})
        for action in copy.actions:
            if action['action_name'] == "send_question":
                obj = Question(action['action_id'])
                obj_copy = obj.recursive_copy(cohort_id)
                action['action_id'] = obj_copy[ID_KEY]
                action["params"]["database_id"] = obj_copy[ID_KEY]
            elif action['action_name'] == "conditional":
                obj = Conditional(action['action_id'])
                obj_copy = obj.recursive_copy(cohort_id)
                action['action_id'] = obj_copy[ID_KEY]
                action["params"]["database_id"] = obj_copy[ID_KEY]
            elif action['action_name'] in ["set_attribute", "send_message"]:
                new_action_id = uuid.uuid4()
                action['action_id'] = new_action_id
            else:
                raise Exception("Recursive copy found an unknown action type!")
        copy.save()
        return copy
    
    def recursive_delete(self):
        for action in self.actions:
            if action['action_name'] == "send_question":
                obj = Question(action['action_id'])
            elif action['action_name'] == "conditional":
                obj = Conditional(action['action_id'])
            else:
                continue
            if obj:
                obj.recursive_delete()
            else:
                log_warning("Bad Action %s" % action["action_id"])
        self.remove()
    
    def serialize_obj_and_actions(self, object_type):
        ret = dict(self)
        ret["actions"] = [self.serialize_action(a) for a in ret["actions"]]
        ret["type"] = object_type
        return ret
    
    def serialize_action(self, action_conf):
        #TODO: make more elegant (and stop using hidden stuff of the action_conf)
        if action_conf["action_name"] == "send_question":
            question = Question(action_conf["params"]["database_id"])
            if not question:
                log_warning("question %s doesn't exist on obj %s" %
                            (action_conf["params"]["database_id"], self[ID_KEY]))
                return None
            return question.serialize_obj_and_actions("question")
        elif action_conf["action_name"] == "set_attribute":
            return {"type": "set_attribute",
                    "attribute_name": action_conf["params"]["attribute_name"],
                    "attribute_value": action_conf["params"]["attribute_value"],
                    "_id": action_conf["action_id"]}
        elif action_conf["action_name"] == "send_message":
            return {"type": "message", "text": action_conf["params"]["text"],
                    "_id": action_conf["action_id"]}
        elif action_conf["action_name"] == "conditional":
            conditional = Conditional(action_conf["params"]["database_id"])
            if not conditional:
                log_warning("conditional %s doesn't exist on obj %s" %
                            (action_conf["params"]["database_id"], self[ID_KEY]))
                return None
            return conditional.serialize_obj_and_actions("conditional")


class Schedule(ActionNode):
    PATH = "backbone.schedules"
    DEFAULTS = {
        "subtype": REQUIRED_STRING,  # options defined in ScheduleTypes
        "cohort_id": REQUIRED,
        "actions": [],
        "question_limit": None,  # For daily_limit schedules
        "send_hour": 19,  # 0 - 23
        "resend_hour": 20,
        "resend_quantity": 2,
        "resend_type": ResendSubtype.time,
        "question_period": 1,  # in days
        # if not empty, used instead of question_period;
        # Takes values 0 - 6, where Sunday = 0, Monday = 1, ...
        "question_days_of_week": [],
        "date": None,
        "create_time": now,
        "modify_time": now, #TODO
        "deleted": False
    }
    
    def serialize(self):
        return self.serialize_obj_and_actions("schedule")

    @classmethod
    def create(cls, data, random_id=True, **kwargs):
        curr_time = now()
        schedule = super(Schedule, cls).create(data, random_id=random_id, **kwargs)
        schedule._create_schedule_executions(curr_time)
        return schedule
    
    def _create_schedule_executions(self, curr_time):
        """ Creates new Schedule executions from newly created schedule """
        from database.tracking.schedule_execution import ScheduleExecution
        from database.backbone.cohorts import Cohort
        from database.tracking.users import Users
        cohort = Cohort(self["cohort_id"])
        users = Users.get_for_cohort_object_id(cohort[ID_KEY])
        for user in users:
            ScheduleExecution.make_execution(user, self[ID_KEY], curr_time)

    def _update_schedule_executions(self, curr_time):
        """ Updates ScheduleExecutions (if not already active) from modified schedules """
        from database.tracking.schedule_execution import ScheduleExecutions
        schedule_executions = ScheduleExecutions(schedule_id=self[ID_KEY], active=False)
        for schedule_execution in schedule_executions:
            schedule_execution.set_period(curr_time, update=True)


class Schedules(DatabaseCollection): OBJTYPE = Schedule

class Conditional(ActionNode):
    PATH = "backbone.conditionals"
    DEFAULTS = {
        "attribute": REQUIRED_STRING,
        "comparison": REQUIRED_STRING,
        "upper_range": "5",
        "comparison_is_attribute": False, # True if the comparison value should be retrieved from a user attribute, does not indicate that comparison and attribute fields are the same
        "subtype": ConditionalSubtype.exactly,
        "cohort_id": REQUIRED,
        "actions": [],
    }

class Conditionals(DatabaseCollection): OBJTYPE = Conditional

class Question(ActionNode):
    PATH = "backbone.questions"
    DEFAULTS = {
        "text": REQUIRED_STRING,
        "cohort_id": REQUIRED,
        "actions": [],
        "parser": Parser.open_ended,
        "min": 1,  # Minimum response number if numeric
        "max": 2,  # Maximum response number if numeric
        "choices": 3,  # Number of choices if multiple choice
        "choices_text": [],  # Lists the multiple choice answer text
        "choices_append": "",
        "auto_append": False,
        "resend": None,  # this is text to prepend on a resend for a bad response
    }

class Questions(DatabaseCollection): OBJTYPE = Question
