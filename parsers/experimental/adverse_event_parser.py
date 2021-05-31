from constants.side_effect_dict import side_effect_dict
from constants.multisymp import multiple_symptoms

locations = ['abdomen', 'agnostic', 'arm', 'back', 'bladder', 'bone', 'breast', 'ear', 'everywhere', 
'extremity', 'eye', 'face', 'female reproductive system', 'genital', 'gums', 'hair','IUD', 'joint', 'leg', 
'mouth', 'muscle', 'nail', 'neck', 'nose', 'pelvis', 'sinus', 'site', 'skin', 'stomach', 'stool', 'throat', 
'tissue', 'tooth', 'urinary tract', 'urine', 'vagina', 'tongue', 'anus']

phenomena = ['bleeding', 'blister', 'cold sensation',  'coldness', 'congestion', 'constriction', 'decay', 
'dilation', 'discharge', 'discoloration', 'disease', 'dizziness', 'dryness', 'failure', 'fungal infection',
'hardness', 'heaviness', 'infection', 'injury', 'irregularity', 'irritation', 'lightness', 'looseness', 'nausea',
'numbness', 'odor', 'pain', 'pricking', 'retention', 'sensitivity to sunlight', 'spasm', 'stiffness', 'swelling', 
'tenderness', 'tightness', 'tingling', 'tinnitus', 'twitching', 'warm sensation', 'warmth', 'restlessness']

properties = ['appetite', 'attention', 'consciousness', 'coordination', 'cough', 'defecation', 'diabetes', 'dream', 'ejaculation', 
'energy', 'erection', 'flatulence', 'heartrate', 'libido', 'life', 'memory',  'mental health', 'mood', 'movement', 'orgasm',
'psyche', 'reflexes', 'sleep', 'sweating', 'taste', 'temperature', 'thirst', 'touch', 'urination', 'vision', 
'weight',  'menstruation', 'speech', 'swallowing', 'alertness', 'personality', 'drug', 'eating']

changes = ['blur', 'calm', 'dearth', 'decrease', 'difficulty', 'excessive', 'hostile', 'increase', 'irregular',
'numb', 'sedate', 'worry', 'frothing', 'fear', 'reaction']

# TODO

def side_effect_parser(msg):
    return [key for key in side_effect_dict if key in msg]

def multiple_symptom_parser(msg):
    return [key for key in multiple_symptoms if key in msg]

def phenomenon_parser(msg):
    return [phe for phe in phenomena if phe in msg]

def location_parser(msg):
    return [loc for loc in locations if loc in msg]

def property_parser(msg):
    return [pro for pro in properties if pro in msg]

def change_parser(msg):
    return [cha for cha in changes if cha in msg]

###############################################################################
##############################   TEST CASES   #################################
###############################################################################

test_cases = {"my anus is bleeding!": {'ph': 'bleeding', 'l': 'anus'},
    "I'm having a heart attack": {'ms': 'heart attack'},
    "Starship Troopers is soooo good it sends chills down my spine": {'se': 'chills'},
    "My libido is in excess of what has commonly come to be seen as excessive": {'pr': 'libido', 'c': 'excessive'}, 
    "my mood is incredibly sedate right now": {'pr': 'mood', 'c': 'sedate'},
    "I think I have severe tooth decay": {'ph': 'decay', 'l': 'tooth'},
    "lately my libido has decreased": {'se': 'libido decrease', 'pr': 'libido', 'c': 'decrease'},
    "i have difficulty breathing": {'pr': 'breath', 'c': 'difficulty'},
    "i'm experiencing flu symptoms": {'ms': 'flu symptoms'},
    "my indigestion! it hurts!": {'ms': 'indigestion'},
    "i'm plagued by wheeziness": {'se': 'wheeziness'},
    "why am I so jittery?": {'ms': 'jittery'},
    "my appetite decreased for the past week": {'se': 'appetite decreased', 'pr': 'appetite', 'c': 'decrease'},
    "i', plagued by rhinitis": {'ms': 'rhinitis'},
    "there is so much congestion in my nose!": {'ph': 'congestion', 'l': 'nose'},
    "i've had difficulty sleeping lately": {'pr': 'sleep', 'c': 'difficulty'},
    "my gums are bleeding!": {'ph': 'bleeding', 'l': 'gums'},
    "my right arm is swelling to a mammoth size": {'ph': 'swelling', 'l': 'arm'},
    "I can't swallow because of the tightness in my throat": {'ph': 'tightness', 'l': 'throat'},
    "my dreams have been incredibly irregular lately": {'pr': 'dream', 'c': 'irregular'},
    "i'm excessively thirsty; always": {'pr': 'thirst', 'c': 'excessive'},
    "my stool suffers from incredible looseness": {'ph': 'looseness', 'l': 'stool'},
    "my vision is blurry!": {'pr': 'vision', 'c': 'blur'},
    "I have a frothing cough": {'pr': 'cough', 'ph': 'frothing'},
    "i'm having difficulty swallowing": {'pr': 'swallowing', 'c': 'difficulty'},
    "the injection site suffers from severe irritation": {'ph': 'irritation', 'l': 'site'},
    "the amount i'm sweating has decreased": {'pr': 'sweating', 'c': 'decrease'},
    "my friends are always commenting about my excessive and explosive flatulence": {'pr': 'flatulence', 'c': 'excessive'},
    "I'm bleeding in my tissue": {'ph': 'bleeding', 'l': 'tissue'},
    "my alertness has severly decrease": {'pr': 'alertness', 'c': 'decrease'},
    "I seem to have suffered death at some point in the past day": {'se': 'death'}, #these first thirty should all work fine
    "It feels like there are nails in my pelvis": {'l': ['nail', 'pelvis']}, #pelvis is the actual location indicated, the nails refer to the construction element and are meant to indicate pain
    "There are an increased number of blisters on my erection": {'pr': 'erection', 'c': 'increase', 'ph': 'blisters'}, #this text actually indicates that the man has blisters on his genitals.
    "the odor from my mouth is so excessive I can taste it!": {'pr': 'taste', 'c': 'excessive', 'ph': 'odor', 'l': 'mouth'}, #while this could indicate some gustatory disturbance, it is probably hyperbolic and addresses the scent
    "I'm having difficulty touching my face": {'pr': 'touch', 'c': 'difficulty', 'l': 'face'}, #this could indicate either sever facial pain or lack of flexibility, but not some failure of the sense of touch
    "the texture of my skin is highly irregular": {'c': 'irregular', 'l': 'skin'}, #here the irregular could indicate any one of a number of problems with the skin
    "My wife has difficulty sleeping due to my excessive and irregular movement": {'pr': ['sleep', 'movement'], 'c': ['difficulty', 'excessive', 'irregular']}, #the difficulty sleeping is a red herring, this is some kind of kinetic disorder
    "I discharge stool with great irregularity": {'c': 'irregular', 'ph': 'irregularity', 'l': 'stool'}, #this probably means that the individual has irregular defecation
    "My irritation knows no bounds!": {'ph': 'irritation'}, #but this probably refers to mood
    "I can't sleep due to my excessively cold temperature": {'pr': ['sleep', 'temperature'], 'c': 'excessive'}, #this person is just cold
    "I keep swallowing back chunks of carrot and bile": {'pr': 'swallowing'}, #but we should tag for vomiting
    "Everything is happening in a blur!": {'c': 'blur'}, #probably confusion
    "the number of high pitched noises i'm hearing has increased": {'pr': 'hearing', 'c': 'increased'}, #tinnitus is hardly super-hearing
    "I burned my tongue so badly I can't taste food anymore": {'l': 'tongue', 'pr': 'taste'}, #this indicates injury/trauma
    "my arm keeps twitching; I think it belongs to someone else": {'ph': 'twitching', 'l': 'arm'}, #this is halfway right, but the mental health issues seem more pressing than simple spasms
    "i can't stop twitching my legs": {'ph': 'twitching', 'l': 'legs'}, #but this may be an indication of restless leg syndrome
    "my memory is decaying": {'pr': 'memory', 'ph': 'decay'}, #but this just indicates memory problems
    "I'm so excessively tired I want to sleep all the time": {'pr': 'sleep', 'c': 'excessive'}, #while this is close to right, we want to figure out they lack energy and are fatigued
    "i have difficulty with the temperature of my face": {'pr': 'temperature', 'c': 'difficulty', 'l': 'face'}, #difficulty is a red herring, this is about flushing or poor facial temperature regulation
    "the injection site is frothing": {'c': 'frothing', 'l': 'site'}, #this needs to get at irritation at injection site
    "sunlight is hostile to be skin": {'c': 'hostile', 'l': 'skin'}, #an odd way to phrase photosensitivity, but then there are many odd people in the world
    "my tongue is consistently bound": {'l': 'tongue'}, #indicating some form of dysphonia
    "my erection is numb": {'pr': 'erection', 'c': 'numb'}, #but really this describes numbness of the genitals
    "my urinary tract keeps spasming": {'ph': 'spasm', 'l': 'urinary tract'}, #this needs to conver to a dynamic prossess
    "I'm having difficulty sleeping due to the constant alien abductions": {'pr': 'sleep', 'c': 'difficulty'}, #once again, the mental issues seem more relevant than the problem detected
    "I can taste blood in the back of my mouth": {'pr': 'taste', 'l': ['back', 'mouth']}, #but we should be concerned about oral bleeding
    "i'm having a slight touch of pain": {'pr': 'touch', 'ph': 'pain'}, #touch here as a word for little bit
    "i seem to be having an excessively hostile reaction to sunlight": {'c': ['excessive', 'hostile']}, #how do we get from here to photosensitivity
    "there's been a decrease in the amount of time I can stand at attention": {'pr': 'attention', 'c': 'decrease'}, #indicates some kind of postural problem, not ADD
    "i experience excessive and unreasonable irritation at the fact that people refuse to believe Starship Troopers the movie is actually my joint; i think i'm going crazy": {'c': 'excessive', 'ph': 'irritation', 'l': 'joint'}, #nothing about the parse gets at the anger issues
    "despite how excessively warm I am, i don't feel thirsty": {'pr': 'thirst', 'c': 'excessive'}, #identifies the opposite of what the message is
    #"my disease is presenting no difficulty, the drug appears to be working": {'pr': 'drug', 'c': 'difficulty', 'ph': 'disease'},""" #concludes the opposite of what it should
    }

for test_case, result in test_cases.iteritems():
    if side_effect_parser(test_case) == result:
        print("OK")
    elif multiple_symptom_parser(test_case) == result:
        print("OK")
    elif phenomenon_parser(test_case) == result:
        print("OK")
    elif location_parser(test_case) == result:
        print("OK")
    elif property_parser(test_case) == result:
        print ("OK")
    elif change_parser(test_case) == result:
        print ("")
    else:
        print("FAILURE: parsing of " + str(test_case) + " != " + str(result))