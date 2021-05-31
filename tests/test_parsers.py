from parsers.yes_or_no_parser import yes_or_no_parser
from parsers.number_parser import number_parser
from utils.testing import MultifailureTest
from tests.common import InstantCensusTestCase
from utils.time import today, timedelta
from parsers.multiple_choice_parser import multiple_choice_parser

class TestParsers(InstantCensusTestCase):
    
    def run_parser_on_cases(self, parser, test_cases):
        with MultifailureTest() as test:
            if isinstance(test_cases, dict):  # For all the 1 element parsers
                for test_inp, result in test_cases.iteritems():
                    ret = parser(test_inp, {"min": 0, "max": 100000})
                    test.assertTrue(ret == result, "'%s' parsed incorrectly: %s != %s"
                                                    % (test_inp, ret, result))
            if isinstance(test_cases, list):  # For the parsers with 2 inputs
                for in_a, in_b, result in test_cases:
                    ret = parser(in_a, {"choices_text": in_b})
                    test.assertTrue(ret == result, "'%s' with %s parsed incorrectly: %s != %s"
                                    % (str(in_a), str(in_b), ret, result))
    
    yes_or_no_parser_tests = {
        #repeats/multiple non conflicting terms
        "yes yes yes yes yes": "yes",
        "no no no no no no": "no",
        #multiple conflicting values
        "yes no": None,
        "no yes": None,
        "yes yes yes no no no yes no no no no": None,
        # no useful values
        "this is a test": None,
        "Pineapples.  I love pineapples and banonos.": None,
        # mixed case
        "YEs": "yes",
        "No": "no",
        #the empty string
        "": None,
        #separators and punctuation removal
        "asdfiadsfksljdnyes no": "no",
        " yes ": "yes",
        "yes ": "yes",
        "yes.": "yes",
        "yes?": "yes",
        " y.": "yes",
        #weird cases of multiple separators and positioning
        "yesterday i met your knowledgable wife, yes": "yes",
        "okey dokey artichoke": "yes",
        "just say no to drugs": "no",
        "i have constantly said no": "no",
        "nah brah": "no",
        "i will make you say that you'll never drink grape soda": "no",
        "did you say that...nevermind I mean yes": "yes",
        "i had aids yesterday with my neighbor tonight, no": "no",  # I'm sorry, whut?
        # the trivial transformation checks
        "y": "yes",
        "yes": "yes",
        "n": 'no',
        "no": 'no',
        #make sure we don't have substring matches
        "had mono yesterday, yes": "yes",
        "had mono yesterday, no": "no"
    }
    
    def test_yes_or_no_parser(self):
        self.run_parser_on_cases(yes_or_no_parser, self.yes_or_no_parser_tests)
    
    number_parser_tests = {
        # basic tests
        "": None,
        "today we will go somewhere tomorrow": None,
        "0": 0,
        "1": 1,
        "1.": 1,
        "12345": 12345,
        "1.0.0": None,
        
        # Multiple numbers
        "84, 200, and 8.": 84,
        "when? I was 5. I had 4 corgies.": 5,
        "when I was 5, I had 4 corgies.": 5,
        "0. .01": 0,  # Python evaluates float('0.') to 0
        
        # Numbers embedded in other strings (we don't want these)
        "g2g today": None,
        "aosjcrrdc2": None,
        "2ojxcga": None,
        "2g": None,
        'g2': None,
        
        #various ordering in sentences, some punctuation
        "4 I have footballs": 4,
        "4 I have 5 footballs": 4,
        "Footballs. I have 4 footballs": 4,
        "I have footballs 5": 5,
        "I have 5 footballs.": 5,
        "my chocolate addiction": None,
        
        # Number punctuation tests
        "1,000": 1000,
        "1, 000": 1,
        "1, .0": 1,
        "I have footballs 5.": 5,  # Trailing valid number punctuation
        "I have footballs 5/": 5,  # Trailing valid number punctuation
        "I have footballs 5/-,.": 5,  # Trailing valid number punctuation
        
        # Throw out bad punctuation strings
        "/.3": 0,
        "...1": None,
        "..1": None,
        "1..": None,
        "\.3": 0,
        ".,34": None,
        "3.,4": None,
        "4./3": 4,
        "3,.4": None,
        "3/,.4": 3,
        "3,/.4": 3,
        "3, /.4": 3,
        "3, oesrudoecnugd 4": 3,
        "3, dog": 3,
        
        # Tests for money
        "$1": 1,
        "$1.35": 1,  # Currently doesn't round, just truncates
        "$1349.1": 1349,
        "$.121": 0,
        "$12.34567": 12,
    #     "test for / naive fraction detection": None,
    
        # Decimal tests
    #     "1.0.": 1,
    #     "3.2": 3.2,
    #     "0.4": 0.4,
    #     ".3": 0.3,
    #     "4 / 16": 0.25,
    #    "3.2 then 3.3": 3.2,
    #     "4.0 I have footballs": 4,
    #     "oh dear. .5 footballs I have": 0.5,
    #     "oh dear,.5 footballs I have": None,
    #     "oh dear, .5 footballs I have": 0.5,
    #     "I have 0.3 footballs": 0.3,
    #     "I have footballs 5.0.": 5.0,
    #     "I have .3 footballs": .3,
        
        #test fraction separator spacing
    #     "I like 1/    4 chickens": 0.25,
    #     "I like 1 /   4 chickens": 0.25,
    #     "I like 1    /4 chickens": 0.25,
    #     "I like 1/4     chickens": 0.25,
        
        # punctuation nonsense
        ".": None,
        " ": None,
        "/": None,
        ",": None,
        ",,": None,
        "..": None,
        "//": None,
        "\\\\": None,
        '\\/': None,
        
        # DEFINITIONAL EDGE CASES EXPLICITLY DEFINED AS RETURNING NONE:
        
        "apple. 1": 1.0,
        "apple.. 1": 1.0,
        "apple... 1": 1.0,  # This is a difficult corner case, invalid-numerical-
        # punctuation-string-including-whitespace, containing a valid-whitespace-
        # separated-numerical-string.
        
        "1..1": None,  # The first two characters of this string evaluate due to
        # weird Python behavior, "float('1.')" returns 1.0.
        
        ########################### number words ###################################
        "one": 1,
        "ten": 10,
        "TEN": 10,
        "TweLV7966E": None,
        "haspjbcr aaar.g uouaosenjr eighteen sraocufdsjbm.997u": 18,
        "1123eighteen3444": None
    }
    
    def test_number_parser(self):
        """
        Currently, IC only supports integers, so number parser should return an int
        """
        self.run_parser_on_cases(number_parser, self.number_parser_tests)
    
    
    multiple_choice_parser_tests = [
        # format, 3-tuple containing: message string, dict of word list, correct output.
        #tests for basic functionality
        ("thing", ['thing'], "thing"),
        ("this is a thing", ["thing", "apples"], "thing"),
        ("i suppose apples", ["thing", "apples"], "apples"),
        #test return only matching the first thing
        ("thing apples", ["thing", "apples"], "thing"),
        ("thingy", ["thing", "apples"], None),
        
        ("asdf", ["", "apples"], None),
        ("asdf", [], None),
        (None, {'apples':123}, None)
    ]
    
    def test_multiple_choice_parser(self):
        self.run_parser_on_cases(multiple_choice_parser, self.multiple_choice_parser_tests)
    
    
    ###############################################################################
    ###################### TESTS FOR EXPERIMENTAL PARSERS #########################
    ###############################################################################
    # from parsers.time_parser import time_parser
    # from parsers.increase_decrease_parser import increase_decrease_parser
    # from parsers.body_part_parser import body_part_parser
    # from parsers.fake_mood_parser import fake_mood_parser
    
    increase_decrease_tests = {
        "asdfiadsfksljdnyes decrease": ("-1", 19, 26),
        "decrease brah": ("-1", 0, 7),
        "increase.": ("1", 0, 7),
        "same": ("0", 0, 3),
        "there has been no change as of now": ("0", 15, 23),
        "it has kind of been the samuel johnson increase power": ("1", 39, 46),
        "you are super awesome except i feel a decreasing power in the force": ("-1", 38, 47),
        "yesterday i was feeling bad but today i feel normal": ("0", 45, 50),
        "today my diarrhea was so bad that it increased the volatility of by butt": ("1", 37, 45),
        " it was an abominable case of sneezing and coughing that was even greater than yesterday ": ("1", 66, 72),
        "i think things went downtown to chinatown but it increased": ("1", 49, 57),
        "ask a different question, bro": None
        }
    
    # def test_increase_decrease_parser():
    #     run_parser_on_cases(increase_decrease_parser, increase_decrease_tests)
    
    
    body_part_parser_tests = {
        "leg": ('leg', 0, 2),
        "legs": ('legs', 0, 3),
        "it costs an arm and a leg": ('arm', 12, 14),
        "legs": ('legs', 0, 3),
        "oh no! my adam's apple": ("adam's apple", 10, 21),
        "don't taze my lower arm,  bro!": ("lower arm", 14, 22),
        "nothing here": None
        }
    
    # def test_body_part_parser():
    #     run_parser_on_cases(body_part_parser, body_part_parser_tests)
    
    time_parser_tests = {
            "3pm      ": (today() + timedelta(hours=15), 0, 2),
            "3p.m": (today() + timedelta(hours=15), 0, 3),
            "3p.m.": (today() + timedelta(hours=15), 0, 4),
            "3 pm": (today() + timedelta(hours=15), 0, 3),
            "3 p.m.": (today() + timedelta(hours=15), 0, 5),
            "3 p.m": (today() + timedelta(hours=15), 0, 4),
            "3 am": (today() + timedelta(hours=3), 0, 3),
            "3 a.m.": (today() + timedelta(hours=3), 0, 5),
            "3am": (today() + timedelta(hours=3), 0, 2),
            "at like 3 a m and it was gross man": (today() + timedelta(hours=3), 7, 17),
            "32": None,
            "nothing here": None
            }
    
    # def test_time_parser():
    #     run_parser_on_cases(time_parser, time_parser_tests)
