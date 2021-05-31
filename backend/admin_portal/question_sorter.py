from sys import maxint

from mongolia import ID_KEY
from mongolia.errors import NonexistentObjectError

from database.analytics.responses import Responses
from database.backbone.schedules import Conditional, Question, Schedule, Schedules
from utils.logging import log_warning


def sorted_list_of_all_questions(cohort):
    """ Return a list of every instance of a question that has been asked in a
    cohort. This list is sorted first by the timestamp that a survey began
    (except that on_user_creation surveys come before any other surveys), and
    within a single survey instance are sorted by the order the questions are
    displayed in the survey builder. If a question was asked 5 times on 5
    different days, that question will appear 5 times in this list.
    This function returns a list of tuples, and each tuple contains two
    elements: the survey_period_start (either the string 'on_user_creation' or a
    datetime object) and the question_id. """
    sorted_question_list = []
    mapping = _get_dict_of_all_sorted_questions(cohort)
    for survey_period_start in _sort_mapping_keys(mapping):
        for question_id in mapping[survey_period_start]:
            sorted_question_list.append((survey_period_start, question_id))
    return sorted_question_list


def get_survey_period_start_time(response):
    """ If the response belongs to an on_user_creation schedule, return the
    string 'on_user_creation'. Otherwise, return the timestamp of the
    survey_period_start, which is when the response's schedule began executing.
    """
    if Schedule(response['schedule_id'])['subtype'] == 'on_user_creation':
        return 'on_user_creation'
    return response['survey_period_start']


def _sort_mapping_keys(mapping):
    unsorted_key_list = mapping.keys()
    sorted_key_list = []
    if 'on_user_creation' in unsorted_key_list:
        unsorted_key_list.remove('on_user_creation')
        sorted_key_list.append('on_user_creation')
    sorted_key_list.extend(sorted(unsorted_key_list))
    return sorted_key_list


def _get_dict_of_all_sorted_questions(cohort):
    ordered_question_schedules = _get_ordered_question_schedules(cohort)
    mapping = _get_all_questions(cohort)
    for survey_period_start_time in mapping:
        questions = _sort_questions_in_one_survey_period(mapping[survey_period_start_time],
                                                        ordered_question_schedules,
                                                        cohort[ID_KEY])
        mapping[survey_period_start_time] = questions
    return mapping


def _sort_questions_in_one_survey_period(questions_dict, ordered_question_schedules, cohort_id):
    questions_list = []
    for question in questions_dict:
        questions_list.append(question)
    schedule_id = _get_most_applicable_schedule_id(cohort_id, questions_dict)
    if schedule_id:
        order_of_questions_in_schedule = ordered_question_schedules[schedule_id]
        # Sort questions by their order in the schedule in the survey builder.
        # If a question isn't in a schedule (likely because someone deleted it
        # from the survey builder, then order it after all the other questions.
        def key_func(x):
            try:
                return order_of_questions_in_schedule.index(x)
            except ValueError:
                return maxint
        questions_list.sort(key=key_func)
    return questions_list


def _get_most_applicable_schedule_id(cohort_id, questions_dict):
    for schedule in Schedules(cohort_id=cohort_id):
        for action in schedule['actions']:
            if action['action_id'] in questions_dict:
                return schedule[ID_KEY]
    if len(Schedules(cohort_id=cohort_id)):
        return Schedules(cohort_id=cohort_id)[0][ID_KEY]
    return None


def _get_all_questions(cohort):
    mapping = {}
    for response in Responses.iterator(cohort_id=cohort[ID_KEY]):
        # Should only happen on test deployments - one of the database entities can be missing
        try:
            survey_period_start_time = get_survey_period_start_time(response)
        except NonexistentObjectError:
            log_warning(
                    "get_survey_period_start_time failed for response %s" % str(response[ID_KEY])
            )
            continue
        question_id = response["question_id"]
        # map question and user id to response object
        if survey_period_start_time not in mapping:
            mapping[survey_period_start_time] = set()
        if question_id not in mapping[survey_period_start_time]:
            mapping[survey_period_start_time].add(question_id)
    return mapping


def _get_ordered_question_schedules(cohort):
    def get_ordered_question_list(action):
        if action['action_name'] == 'conditional':
            conditional = Conditional(action['params']['database_id'])
            for action in conditional['actions']:
                get_ordered_question_list(action)
        elif action['action_name'] == 'send_question':
            question = Question(action['params']['database_id'])
            schedules[schedule[ID_KEY]].append(question[ID_KEY])
            for action in question['actions']:
                get_ordered_question_list(action)
    
    schedules = {}
    for schedule in Schedules(cohort_id=cohort[ID_KEY]):
        schedules[schedule[ID_KEY]] = []
        for action in schedule['actions']:
            get_ordered_question_list(action)
    return schedules
