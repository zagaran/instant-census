from constants.dates import PREFIXES, SINGULAR, LEVELS, MONTHS, DAYS, TENSES, PATTERNS, TENSED
from parsers.number_parser import number_parser
from utils.time import timedelta, now, datetime
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU
from re import search

DOWS = {"monday": MO, "tuesday": TU, "wednesday": WE, "thursday": TH, "friday": FR, "saturday": SA, "sunday": SU}

def date_parser(msg):
    for day_name, day in TENSES.items():
        if day_name in msg:
            return (now() + timedelta(days=day), msg.index(day_name), search(day_name,msg).end())
    
    msg = msg.replace("/", "-")
    for pattern in PATTERNS:
        find = search(pattern, msg)
        if find:
            result = date_pattern(msg[find.start(): find.end()])
            return (result, find.start(), find.end() - 1)
    
    day, month, year, begin, end = 0, 0, 0, 0, 0
    for prefix in PREFIXES:
        if search(prefix + "\d\d",msg):
            begin = search(prefix + "\d\d",msg).start()
            year = int(number_parser(msg[begin : search(prefix + "\d\d",msg).end()])[0])
            if year < now().year - 1990 + 10: year += 2000
            if year < 100: year += 1900
    for month_name, month_number in MONTHS.items():
        if month_name in msg: 
            month = month_number
            if (search(month_name,msg).end() > begin + end): end = search(month_name,msg).end() 
            if (msg.index(month_name) < begin or begin == -1): begin = msg.index(month_name)
            break
    for day_name, day_number in DAYS.items():
        if day_name in msg:
            day = day_number
            if(search(day_name,msg).end() > begin + end): end = search(day_name,msg).end()
            if (msg.index(day_name) < begin): begin = msg.index(day_name)
            break
    if int(day) > 0 and int(month) > 0 and int(year) > 0: return (datetime(int(year),month,day), begin, end)
    if day > 0 and month > 0 and year == 0:
        if now().month < month: year = now().year - 1
        else: year = now().year
        return (datetime(year,month,day), begin, end)
    
    if "from now" in msg:
        for day_name, day in LEVELS.items():
            if day_name in msg:
                return (now() + timedelta(days = day * int(number_parser(msg)[0])),
                        number_parser(msg)[1], msg.index("now") + 3)
        for day_name, day in SINGULAR.items():
            if day_name in msg:
                return (now() + timedelta(days = day),
                                        msg.index(day_name), msg.index("now") + 3)
    else:
        for tense_word, tense in TENSED.items():
            for day_word, day in DOWS.items():
                match_string = tense_word + " " + day_word
                if match_string in msg:
                    ret = now() + relativedelta(days=tense, weekday=day(tense))
                    begin = msg.index(match_string)
                    return(ret, begin, search(match_string, msg).end())
        for day_name, day in SINGULAR.items():
            futurewords = "next "+ day_name
            if futurewords in msg: return (now() + timedelta(days=day), msg.index(futurewords), search(day_name,msg).end())
            pastwords = day_name + " ago"
            if pastwords in msg: return (now() + timedelta(days=-day), msg.index(pastwords), msg.index(" ago") + 4)
        for day_name, day in LEVELS.items():
            day = number_parser(msg)
            if day and day_name in msg:
                return (now() + timedelta(days=-int(day[0])),
                        number_parser(msg)[1], search(day_name, msg).end())
    return None
    
def date_pattern(date_string):
    mdy = date_string.split("-")
    if (len(mdy[2]) == 4):
        return datetime(int(mdy[2]), int(mdy[1]), int(mdy[0]))
    if (len(mdy[0]) == 4):
        return datetime(int(mdy[0]), int(mdy[1]), int(mdy[2]))
    if (len(mdy[0]) <= 2 and len(mdy[1]) <= 2 and len(mdy[2]) <= 2):
        if int(mdy[2]) > now().year - 2000: 
            return datetime(int(mdy[2]) + 1900, int(mdy[0]), int(mdy[1]))
        else:
            return datetime(int(mdy[2]) + 2000, int(mdy[0]), int(mdy[1]))
            