unitDefinitions = [
    ("zero",       0),
    ("one",        1),
    ("two",        2),
    ("three",      3),
    ("few",        3),
    ("four",       4),
    ("five",       5),
    ("six",        6),
    ("seven",      7),
    ("eight",      8),
    ("nine",       9),
    ("ten",       10),
    ("eleven",    11),
    ("twelve",    12),
    ("thirteen",  13),
    ("fourteen",  14),
    ("fifteen",   15),
    ("sixteen",   16),
    ("seventeen", 17),
    ("eighteen",  18),
    ("nineteen",  19),
    ]
#units = Or( [ makeLit(s,v) for s,v in unitDefinitions ])
tensDefinitions = [
    ("ten",     10),
    ("twenty",  20),
    ("thirty",  30),
    ("forty",   40),
    ("fourty",  40),
    ("fifty",   50),
    ("sixty",   60),
    ("seventy", 70),
    ("eighty",  80),
    ("ninety",  90),
    ]
#tens = Or( [ makeLit(s,v) for s,v in tensDefinitions ] )
hundreds = ("hundred", 100)
majorDefinitions = [
    ("thousand",    int(1e3)),
    ("million",     int(1e6)),
    ("billion",     int(1e9)),
    ("trillion",    int(1e12)),
    ("quadrillion", int(1e15)),
    ("quintillion", int(1e18)),
    ]
#mag = Or( [ makeLit(s,v) for s,v in majorDefinitions ] )

#wordprod = lambda t: reduce(mul,t)
#wordsum = lambda t: sum(t)
#numPart = (((( units + Optional(hundreds) ).setParseAction(wordprod) + 
#               Optional(tens)).setParseAction(wordsum) 
#               ^ tens )
#               + Optional(units) ).setParseAction(wordsum)
#numWords = OneOrMore( (numPart + Optional(mag)).setParseAction(wordprod) 
#                    ).setParseAction(wordsum) + StringEnd()
#numWords.ignore("-")
#numWords.ignore(CaselessLiteral("and"))

"""
units = {"zero": 0, "one": 1, "two" = 2, "three" = 3, "four" = 4,  "five" = 5, 
    "six" = 6, "seven" = 7, "eight" = 8, "nine" = 9}

teens = ["", "eleven", "twelve", "thirteen", "fourteen", 
    "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]

tens = ["", "ten", "twenty", "thirty", "forty",
    "fifty", "sixty", "seventy", "eighty", "ninety"]
"""