from tests.common import InstantCensusTestCase
from utils.parser_helpers import split_standard_separators
# from parsers.number_parser import text2int
from string import whitespace as WHITESPACE_CHARS


class TestParserHelpers(InstantCensusTestCase):
    SPLIT_STRING_TESTS = {
        #simple splitting cases
        'a,b': ['a', 'b'],
        'a,b,c': ['a', 'b', 'c'],
        'a,bc': ['a', 'bc'],
        'a b c': ['a', 'b', 'c'],
        #multiple separators in a row
        "a, b, c": ['a', 'b', 'c'],
        
        #individual splitter character tests
        "-": [],
        ",": [],
        ".": [],
        "/": [],
        ";": [],
        ":": [],
        "|": [],
        WHITESPACE_CHARS: [],
    }
    
    def test_split_string(self):
        for test_inp, result in self.SPLIT_STRING_TESTS.iteritems():
            ret = split_standard_separators(test_inp)
            self.assertTrue(ret == result, "'%s' parsed incorrectly: %s != %s" %
                            (test_inp, ret, result))

# text2int_tests = {
#     "twenty-two" : 22,
#     "ninety seven" : 97,
#     "one hundred thirty seven" : 137,
#     "one million" : 1000000,
#     "fiftieth" : 50,
#     "four-hundred and forty-fourth" : 444,
#     "eighty" : 80,
#     "ten thousand and one" : 10001,
#     }

# def test_text2int():
#     with Test() as test:
#         for test_inp, result in text2int_tests.iteritems():
#             ret = text2int(test_inp)
#             test.assertTrue(ret == result, str(test_inp) + " parsed incorrectly: " +
#                                     str(ret) + " != " + str(result))
