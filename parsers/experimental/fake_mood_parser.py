from constants.parsers import GOOD_MOOD_LIST, BAD_MOOD_LIST, NEUTRAL_MOOD_LIST
from utils.parser_helpers import split_string
from utils.decorators import Parser

@Parser
def fake_mood_parser(msg):
    #ancient todo: standardize msg cleaning w/ function, where is current cleaning
    msg_words = split_string(msg, " ,.!?\/;@#$%^&*()")
    catch = False
    for (good, bad, neutral) in map(None, GOOD_MOOD_LIST, BAD_MOOD_LIST, NEUTRAL_MOOD_LIST):
        for word in msg_words:
            if good:
                if word == good:
                    val = '1'
                    catch = True
            if bad:
                if word == bad:
                    val = '-1'
                    catch = True
            if neutral:
                if word == neutral:
                    val = '0'
                    catch = True
            if catch:
                begin = msg.index(word)
                return (val, begin, begin + len(word) - 1)
    return None
