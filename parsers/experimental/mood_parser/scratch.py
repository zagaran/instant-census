from nltk.corpus import wordnet as wn


def main():
	"""build wordnets from standard list"""

	word_nets = []
	mood_list = open("mood_list.txt","r").readlines()

	for m in mood_list:
		m = m.replace('\n', '')
		raw_input()
		print "MOOD :", m
		synonyms = wn.synsets(m, pos=wn.ADJ)
		print synonyms
		for synonym in synonyms:
			for lem in synonym.lemmas:
				print lem.name



if __name__ == '__main__':
	main()