import random
import hashlib
import uuid
import string
from constants.password_word_list import word_list
from utils.time import now
from datetime import timedelta

PASS_LENGTH = 8
PASS_CHARS = list(set(string.ascii_uppercase + string.digits) -
                  set(['I', 'O', '1', '0', 'S', '5']))

def generate_access_code():
    return ''.join(random.choice(PASS_CHARS) for i in range(PASS_LENGTH))  # @UnusedVariable

def generate_temp_pass():
    return (random.choice(word_list) + " " + random.choice(word_list) + " " +
            random.choice(word_list) + " " + random.choice(word_list))

def random_hex():
    return uuid.uuid4().hex

def hash_password(password, salt):
    return hashlib.sha512(password + salt).hexdigest()

def code_expiration():
    return now() + timedelta(days=30)

def looks_like_an_access_code(message):
    return len(message.strip()) >= 6

def random_string(length=40):
    return "".join(random.choice(string.letters + string.digits) for _ in range(length))
