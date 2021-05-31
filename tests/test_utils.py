from datetime import datetime, timedelta
from tests.common import InstantCensusTestCase
from utils.time import days_in_question_period


class TestUtils(InstantCensusTestCase):
    
    def test_days_in_question_period(self):
        every_day = [0, 1, 2, 3, 4, 5, 6]
        sunday = [0]
        monday = [1]
        for i in range(7):
            # June 7, 2015 was a Sunday
            start_time = datetime(2015, 6, 7) + timedelta(days=i)
            days = days_in_question_period(start_time, every_day)
            # isoweekday has Monday == 1 ... Sunday == 7
            self.assertEqual(days, 1, "day of week %s gave %s against every_day"
                             % (start_time.isoweekday(), days))
        for i in range(7):
            # June 7, 2015 was a Sunday
            start_time = datetime(2015, 6, 7) + timedelta(days=i)
            days = days_in_question_period(start_time, sunday)
            # isoweekday has Monday == 1 ... Sunday == 7
            self.assertEqual(days, 7 - i, "day of week %s gave %s against sunday"
                             % (start_time.isoweekday(), days))
        for i in range(7):
            # June 8, 2015 was a Monday
            start_time = datetime(2015, 6, 8) + timedelta(days=i)
            days = days_in_question_period(start_time, monday)
            # isoweekday has Monday == 1 ... Sunday == 7
            self.assertEqual(days, 7 - i, "day of week %s gave %s against monday"
                             % (start_time.isoweekday(), days))
