#Code of text2int from StackOverflow. Used under CC BY-SA.
#Original can be found at http://stackoverflow.com/a/598322

# numwords for use in number_parser, _textnum_parse, text2int etc.
numwords = {
'and': (1, 0),
'twelve': (1, 12),
'seven': (1, 7),
'trillion': (1000000000000L, 0),
'ten': (1, 10),
'seventeen': (1, 17),
'two': (1, 2),
'four': (1, 4),
'zero': (1, 0),
'eighteen': (1, 18),
'thirteen': (1, 13),
'': (1, 10),
'one': (1, 1),
'fifty': (1, 50),
'nineteen': (1, 19),
'six': (1, 6),
'three': (1, 3),
'quadrillion': (1000000000000000L, 0),
'eleven': (1, 11),
'decillion': (1000000000000000000000000000000000L, 0),
'septillion': (1000000000000000000000000L, 0),
'hundred': (100, 0),
'quintillion': (1000000000000000000L, 0),
'thousand': (1000, 0),
'million': (1000000, 0),
'eighty': (1, 80),
'fourteen': (1, 14),
'five': (1, 5),
'sixty': (1, 60),
'sixteen': (1, 16),
'fifteen': (1, 15),
'seventy': (1, 70),
'billion': (1000000000, 0),
'forty': (1, 40),
'thirty': (1, 30),
'nonillion': (1000000000000000000000000000000L, 0),
'sexillion': (1000000000000000000000L, 0),
'ninety': (1, 90),
'nine': (1, 9),
'twenty': (1, 20),
'eight': (1, 8),
'octillion': (1000000000000000000000000000L, 0)
}

ordinal_words = {
'first':1,
'second':2,
'third':3,
'fifth':5,
'eighth':8,
'ninth':9,
'twelfth':12
}

ordinal_endings = [('ieth', 'y'), ('th', '')]
