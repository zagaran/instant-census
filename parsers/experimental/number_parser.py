from parsers.number_parser import _text2int
from fractions import Fraction
from constants.dates import NUMBERS

def number_parser(msg):
    # test cases: "4 / 16", "twenty-first", "first", "one hundred thirty seven", "tenth", "1,234"
    begin = -1
    length = -1
    num = ' '.join(msg.split())
    #num = msg.replace(',', '')
    try:
        num = int(num)
        begin = msg.index(str(num))
        length = len(str(num)) - 1
    except ValueError:
        try:
            num = float(num)
            begin = msg.index(str(num))
            length = len(str(num)) - 1
        except ValueError:
            try:
                num = float(Fraction(num))
                isint = False
                for each in msg[:msg.index("/")]:
                    try:
                        if(int(each)):
                            isint = True
                        if isint == True:
                            begin = msg.index(each)
                        isint = False
                    except Exception:
                        pass
                    if begin > -1:
                        break
                for each in msg[msg.index("/") + 1:]:
                    try:
                        if(int(each)):
                            isint = True
                        if isint == True:
                            shortmsg = msg[msg.index("/") + 1:]
                            count = shortmsg.count(each)
                            length = shortmsg.index(each) + len(msg[begin:msg.index("/")]) + 1 + count
                        isint = False
                    except Exception:
                        pass
            except ValueError:
                try:
                    if not "/" in msg and msg.isdigit() == False:
                        begin = _text2int(num)[1]
                        length = _text2int(num)[2]
                        num = _text2int(num)[0]
                except ValueError:
                    return False
    return (num, begin, length)
    
def number_parser2(msg):
    num = 0; start = -1
    for each in range(len(msg)):
        if msg[each].isdigit() and (msg[each - 1].isdigit() or msg[each + 1].isdigit()):
            num *= 10
            num += int(msg[each])
            if start == -1: start = msg.index(each)
        elif num == 0 and msg[each].isdigit():
            num *= 10
            num += int(msg[each])
        if each == 0 and msg[each].isdigit() and not msg[each + 1].isdigit():
            num = int(msg[each])
            start = 0
    for name, number in NUMBERS.iteritems():
        if name in msg:
            num = number
            if start == -1:
                start = msg.index(name)
    return (num, start)
