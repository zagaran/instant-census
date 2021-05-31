from parsers.experimental.mood_parser import mood_parser
from parsers.experimental.date_parser import date_parser
from utils.testing import Test
from tests.parser_tests import __parser_test
from utils.time import timedelta, now, datetime
from dateutil.relativedelta import relativedelta, WE, TH

def test_drug_parser():
    pass

mood_parser_tests = {
        "depressed": (-1.0, 0, 8),
        "I am depressed": (-1.0, 5, 13),
        }
"""
print mood_parser("happy") #.7
print mood_parser("sad") #-.6
print mood_parser("depressed") #returns neutral
print mood_parser("I am upset") #-.6
print mood_parser("I'm feeling down") #-.6
print mood_parser("I am really happy!!") #lower value than just plain "happy" - .6
print mood_parser("I'm not feeling good") #-.5
print mood_parser("I'm excited") #should be higher (.5)
print mood_parser("I'm having a really bad day") #good! could be a little higher (currently at -.9)
print mood_parser("I'm really depressed") #good (-.7)
print mood_parser("I'm kind of depressed") #good (-.6)
print mood_parser("I'm elated") #WRONG (-.6)

print mood_parser("Calm") #okay
print mood_parser("Amused") #WRONG (-.5)
print mood_parser("Anger") #WRONG (0)
print mood_parser("Anticipation") #WRONG (0)
print mood_parser("Cold") #??? (-.6)
#print mood_parser("""


def test_mood_parser():
    __parser_test(mood_parser, mood_parser_tests)

date_parser_tests = {
    "1978-01-28": datetime(1978, 1, 28),
    "1984/04/02": datetime(1984, 4, 2),
    "1/02/1980": datetime(1980, 1, 2),
    "2/28/79": datetime(1979, 2, 28),

    "jan 20, 2013": datetime(2013, 1, 20),
    "january 20, 2013": datetime(2013, 1, 20),
    "01-6-13": datetime(2013, 1, 6),
    "aug 12": datetime(2012, 8, 12),
    "fri, 21 nov 1997": datetime(1997, 11, 21),
    "jan 21, '97": datetime(1997, 1, 21),
    "sun, nov 21": datetime(2012, 11, 21),
    "jan 1st": datetime(2013, 1, 1),
    "february twenty-eighth": datetime(2013, 2, 28),

    "today": now(),
    "yesterday": now() - timedelta(days=1),
    "next thursday" : now() + relativedelta(days=+1, weekday=TH(+1)),
    "last wednesday": now() + relativedelta(days=-1, weekday=WE(-1)),
    "tomorrow": now() + timedelta(days=1),
    "next week": now() + timedelta(days=7),
    "next month": now() + relativedelta(months = 1),
    "next year": now() + relativedelta(years = 1),
    "3 days from now": now() + timedelta(days=3),
    "three weeks ago": now() + timedelta(days=-21),
    "two weeks from now": now() + timedelta(days=14),
    "a month ago": now() + relativedelta(months = -1),
    "3 days ago": now() + timedelta(days=-3),
    "the other day": now() + timedelta(days=-3),
}

def test_date_parser():
    with Test() as test:
        for test_case, result in date_parser_tests.iteritems():
            ret = date_parser(test_case)
            if ret is None: test.assertTrue(ret is not None, str(test_case) + " parsed to None")
            else: test.assertTrue(ret[0] == result, str(test_case) + " parsed incorrectly: " +
                                  str(ret[0]) + " != " + str(result))

severity_parser_tests = {
    "none": (0, 0, 3),
    "I have none": (0, 7, 10),
    "yes, and it was terrible": (5, 16, 23),
    "yes, and it was not terrible": (3.5, 16, 27),
    "moderate": (3, 0, 7),
    "very bad": (4.4, 0, 7),
    "not bad": (2.8, 0, 6),
    "not very bad": (3.08, 4, 11),
    "nothing here" : None
    }

def test_severity_parser():
    __parser_test(severity_parser, severity_parser_tests)

