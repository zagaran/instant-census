def index_tracker(key, msg):
	"""
		This function is meant to track the start and end index of
		a key in a message.
		Takes in: (key : string) (msg : string)
		Does: Calls helper_track when the first char of key matches a char in msg 
		  to determine if the entire key string matches
		returns tuple (True, start, finish) if in msg else false
	"""
	key = ''.join(key.split())
	start, finish = 0, 0
	for each in range(0, len(msg)):
		if msg[each] == key[0]:
			if len(key) > 1 and len(msg) > each + 1:
				ret = helper_track(key[1:], msg, each + 1)
				if ret[0]:
					return (True, each, ret[1])
			else:
				return (True, each, each)
		else:
			continue
	return None


def helper_track(key, msg, msgindex):
	"""
		This function is meant to track if entire key exists in msg,
		takes in: (key : string) (msg : string) (msgindex : int)
		does: checks if the next char in key matches next char in msg
		returns (True, end index) if whole char exists else False
	"""
	if key is '':
		return (True, msgindex - 1)
	elif msg is '':
		return (False, msgindex - 1)
	elif msg[msgindex] == ' ' and len(msg) > msgindex + 1:
		return helper_track(key, msg, msgindex + 1)
	else:
		if key[0] == msg[msgindex] and len(key) >= 1 and len(msg) > msgindex:
			# print key, msg, msg[msgindex], msgindex, len(msg)
			return helper_track(key[1:], msg, msgindex + 1)
		else:
			return (False, msgindex)


def split_str(text, separator):
    words = []
    word = ""
    for each in range(0, len(text)):
    	if text[each] != separator:
    		if word == "" and text[each] == ' ':
    			continue
    		else:
    			word += text[each]
    			if each == (len(text) - 1):
    				words.append(remove_end_spaces(word))
    	else:
    		words.append(remove_end_spaces(word))
    		word = ""
    		continue
    return words

def remove_end_spaces(text):
	if text == '' or text[-1] != ' ':
		return text
	else:
		return remove_end_spaces(text[:-1])

def join_str(text, seperator):
	new_text = ""
	for each in text:
		if new_text == "":
			new_text += each
		else:
			new_text += seperator + each
	return new_text
