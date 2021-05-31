from utils.parser_helpers import split_standard_separators

def multiple_choice_parser(msg, question):
    """ Takes text and a dictionary/set of words.  Parses the text for the first
    word in the supplied dictionary, and returns the corresponding dictionary entry."""
    if msg is None: return None
    # TODO: update when question choices changes to dict
    words_dict = dict((i.lower(), i) for i in question["choices_text"])
    
    msg = msg.lower()
    
    if msg in words_dict:
        return words_dict[msg]
     
    msg_words = split_standard_separators(msg)
    for word in msg_words:
        if word in words_dict:
            return words_dict[word]
    
    return None