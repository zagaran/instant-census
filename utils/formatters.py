from re import compile, search
from constants.exceptions import BadPhoneNumberError
import unicodedata
from conf.settings import ALLOW_INTERNATIONAL_SENDING
from utils.server import PRODUCTION
from constants.area_code_mapping import test_area_codes, area_code_mapping,\
    state_abbreviations, country_calling_code_mapping

# pattern strips out everything except digits or '+'
PHONE_PATTERN = compile(r'[^\d\+]+')
# pattern matches all NON-allowed characters for parsing (anything that isn't in ascii 32-126,
# viewable by "import string; string.printable[:-5]")
PARSER_PATTERN = compile(r"[^ -~]+")

UNICODE_WARNING_MSG = "[UNICODE REMOVED]" # unicode not supported in data downloads

COMMON_UNICODE_MAP = {
    u'\u201c': '"', #left double smart quote 0x201C
    u'\u201d': '"', #right double smart quote 0x201D
    u'\u2018': "'", #left single smart quote 0x2018
    u'\u2019': "'", #right single smart quote 0x2019
    u'\u2014': "-", #em dash 0x2014
    u'\u2013': "-", #en dash 0x2013
}

def phone_format(pn):
    """
        TODO: instead of searching just for alpha, do negative regex on allowed characters to detect 
        phone numbers with incorrect e.g. '&' or '$'
        allowed_char_pattern = re.compile(r'[^?!\d\+\(\)\-\. ]+')
    """
    
    if search('[a-zA-Z]', pn) or pn.count("+") > 1:
        raise BadPhoneNumberError("Invalid phone number: " + str(pn))
    pn = PHONE_PATTERN.sub("", pn)
    if ALLOW_INTERNATIONAL_SENDING:
        return intl_phone_format(pn)
    else:
        return nanp_phone_format(pn, True)


def phone_humanize(pn):
    if ALLOW_INTERNATIONAL_SENDING:
        if pn.startswith("+1"):
            return "%s (%s) %s-%s" % (pn[0:2], pn[2:5], pn[5:8], pn[8:12])
        pnx = pn.strip("+")
        for key in country_calling_code_mapping:
            if pnx.startswith(key):
                ccc_len = len(key) + 1
                return "%s %s" % (pn[0:ccc_len], pn[ccc_len:])  
    pn = phone_format(pn)[2:]
    return "(%s) %s-%s" % (pn[0:3], pn[3:6], pn[6:10])


def intl_phone_format(pn):
    if pn.startswith("+") and not pn.startswith("+1"):
        pnx = pn.strip("+")
        for key in country_calling_code_mapping:
            if pnx.startswith(key):
                return pn
    return nanp_phone_format(pn)


def nanp_phone_format(pn, domestic=False):
    if len(pn) == 11 and not pn.startswith("+") and pn.startswith("1"):
        pn = "+" + pn
    elif len(pn) == 10:
        pn = "+1" + pn
    elif not len(pn) == 12 or not pn.startswith("+1"):
        raise BadPhoneNumberError("Invalid phone number: " + str(pn))
    area_code = pn[2:5]
    if not PRODUCTION and area_code in test_area_codes:
        return pn
    try:
        state = area_code_mapping[area_code][0]
    except KeyError:
        raise BadPhoneNumberError("Invalid phone number: " + str(pn))
    if not domestic or state in state_abbreviations:
        return pn
    raise BadPhoneNumberError("Invalid phone number: " + str(pn)) 
    
    
def parser_format(text, lower_caps=True, purge_unicode=True, sub=True):
    # strips trailing whitespace
    text = text.strip()
    #TODO: figure out wheter we should to strip unicode
    if purge_unicode:
        text = remove_unicode(text)
    if lower_caps:
        text = text.lower()
    if sub:
        text = PARSER_PATTERN.sub("", text)
    return text


def remove_unicode(text, msg_append=False):
    """Removes unicode"""
    if isinstance(text, int) or isinstance(text, float):
        text = str(text)
    if isinstance(text, unicode):
        unicode_removed = unicodedata.normalize("NFKD", text).encode("ascii", "replace").decode("utf-8")
        if not msg_append:
            return unicode_removed
        return unicode_removed + UNICODE_WARNING_MSG
    text = text.strip()
    return text


def convert_unicode(text):
    if text is None:
        return None
    if isinstance(text, basestring):
        for k, v in COMMON_UNICODE_MAP.items():
            text = text.replace(k, v)
    return text

def encode_unicode(text):
    """ This method needs to handle input types: None, unicode, basestring, int, float"""
    if text is None:
        return None
    if isinstance(text, unicode):
        return text.encode('utf-8')
    if isinstance(text, basestring):
        return text.encode('ascii')
    # ints, floats
    return text
    
