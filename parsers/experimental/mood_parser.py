#from parsers.spell_checker import correct
from constants.parsers import MOOD_FIX_LIST
from pattern.en import polarity

def mood_parser(msg):
    for word in msg:
        #cword = correct(word)
        if word in MOOD_FIX_LIST:
            adjusted_probability = MOOD_FIX_LIST[word]
            return (adjusted_probability, msg.index(word), len(word))
    adjusted_probability = (polarity(msg) * 10) / 10
    return (adjusted_probability, 0, len(msg))