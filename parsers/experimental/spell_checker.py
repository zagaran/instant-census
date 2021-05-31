from constants import drug_list, bodypart_list
import re, collections

def contractionFixer(text):
    dictionary = {"couldnt": "could not", "couldn't": "could not", "shouldnt": "should not", "shouldn't": "should not",
                  "id": "i would", "i'd": "i would", "i've": "i have", "ive": "i have", "aren't": "are not", "arent": "are not",
                  "can't": "can not", "cant": "can not", "couldn't": "could not", "couldnt": "could not", "didn't": "did not", "didnt": "did not",
                  "doesn't": "does not", "doesnt": "does not", "don't": "do not", "hadn't": "had not", "hadnt": "had not", "hasn't": "has not",
                  "hasnt": "has not", "haven't": "have not", "havent": "have not", "he'd": "he would", "he'll": "he will", "he's": "he is",
                  "hes": "he is", "i'll": "i will", "i'm": "i am", "im": "i am", "isn't": "is not", "isnt": "is not", "let's": "let us", "lets": "let us",
                  "mightn't": "might not", "mightnt": "might not", "mustn't": "must not", "mustnt": "must not", "shan't": "shall not", "shant": "shall not",
                  "she'd": "she would", "she'll": "she will", "she's": "she is", "shes": "she is", "that's": "that is", "thats": "that is", "there's": "there is",
                  "theres": "there is", "they'd": "they would", "theyd": "they would", "they'll": "they will", "they'll": "they will", "they're": "they are",
                  "they've": "they have", "theyve": "they have", "we'd": "we would", "we're": "we are", "we've": "we have", "weve": "we have",
                  "weren't": "were not", "werent": "were not", "what'll": "what will", "whatll": "what will", "what're": "what are", "whatre": "what are",
                  "what's": "what is", "whats": "what is", "what've": "what have", "whatve": "what have", "where's": "where is", "wheres": "where is",
                  "who'd": "who would", "whod": "who would", "who'll": "who will", "wholl": "who will", "who're": "who are", "who are": "who are",
                  "who's": "who is", "whos": "who is", "who've": "who have","won't": "will not", "wont": "will not","wouldn't": "would not",
                  "wouldnt": "would not", "you'd": "you would", "youd": "you would", "you'll": "you will", "youll": "you will", "you're": "you are",
                  "youre": "you are", "you've": "you have", "youve": "you have"}
    for contraction, full in dictionary.iteritems():
        if contraction in text:
            return full

def textFixer(text):
    textdictionary = {"lol": "(I found this amusing)", " ha ": "(I found this amusing)", "hah": "(I found this amusing)", "fml": "(This was a bad incident)"}
    for short, long in textdictionary.iteritems():
        if short in text:
            return long

def words(text): return re.findall('[a-z]+', text.lower())

def train(features):
    model = collections.defaultdict(lambda: 1)
    for f in features:
        model[f] += 1
    return model

NWORDS = train(words(open('constants/big.txt').read()))

alphabet = 'abcdefghijklmnopqrstuvwxyz'

def edits1(word):
    splits     = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes    = [a + b[1:] for a, b in splits if b]
    transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b)>1]
    replaces   = [a + c + b[1:] for a, b in splits for c in alphabet if b]
    inserts    = [a + c + b     for a, b in splits for c in alphabet]
    return set(deletes + transposes + replaces + inserts)

def known_edits2(word):
    return set(e2 for e1 in edits1(word) for e2 in edits1(e1) if e2 in NWORDS)

def known(words): return set(w for w in words if w in NWORDS)

def exception(exceptions, brand, text):
    for e in exceptions:
        if (brand in e) and (e in text): return True
    return False

def drug_body_parser(msg):
    for drug in drug_list.order:
        current_drug = drug_list.drug_list[drug]
        exceptions = current_drug['exceptions'] if 'exceptions' in current_drug else []
        for misspelling in current_drug['spellings']:
            if misspelling in msg and not exception(exceptions, misspelling, msg):
                return drug
    for bp in bodypart_list.order:
        if bp in msg: return bp

# pass string into 'correct' function
def correct(word):
    contractionFixer(word)
    if not textFixer(word) is None: return textFixer(word)
    elif not contractionFixer(word) is None: return contractionFixer(word)
    elif not drug_body_parser(word) is None: return drug_body_parser(word)
    candidates = known([word]) or known(edits1(word)) or known_edits2(word) or [word]
    return max(candidates, key=NWORDS.get)

print correct("sucessuful")
print correct("wendesday")
print correct("yas")
print correct("couldnt")
print correct("druk")
print correct("lol")
