from constants import drug_list
from utils.parser_helpers import exception

def drug_parser(msg):
    users_drugs = []
    start = []
    finish = []
    for drug in drug_list.order:
        current_drug = drug_list.drug_list[drug]
        exceptions = current_drug['exceptions'] if 'exceptions' in current_drug else []
        for misspelling in current_drug['spellings']:
            if misspelling in msg and not exception(exceptions, misspelling, msg):
                users_drugs.append(drug)
                start.append(msg.index(misspelling))
                finish.append(start[len(start) - 1] + len(misspelling))
    if users_drugs:
        return (users_drugs, start, finish)
    else: return False

