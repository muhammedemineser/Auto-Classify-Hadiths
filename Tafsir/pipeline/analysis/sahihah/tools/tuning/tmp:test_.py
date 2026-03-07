from collections import defaultdict

txt = [
    "the prophet said",
    "in the name of god",
    "the prophet said",
    "pray five times",
    "in the name of god",
    "the prophet said",
    "give to the poor",
]

def cand_txt():
    global cand_txt
    for i, line in enumerate(txt):
        cand_txt[line].append(i)
    dict(cand_txt)

cand_txt()
print(cand_txt)