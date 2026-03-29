import re
from statistics import multimode, stdev, mode
import random as ra
from pprint import pprint

seq = 1
grouped = {}
path = "/home/mo/desk/apps/classify/chunks_with_most_isnad_elements.xml"
with open(path) as f:
    doc = f.readlines()
    for line in doc:
        match = re.match(r"^(\d+)?\|", line)
        if match:
            match = (
                int(match.group(1))
                if match.group(1) is not None
                else f"noId{ra.random()}"
            )
            seq = match
            grouped[seq] = [line]
        else:
            grouped[seq].append(line)


# pprint(grouped)
lens = {}  # { id : len([tokens]) }
for k, list_of_tokens in grouped.items():
    for tokens in list_of_tokens:
        tokens = tokens.split()
        if k not in lens:
            lens[k] = len(tokens)
        else:
            lens[k] += len(tokens)

token_length = {}  # { len(tokens) : .count() }
for k, v in lens.items():
    if v not in token_length:
        token_length[v] = 1
    else:
        token_length[v] += 1

most_common = {
    mode(list(token_length.keys())): v
    for k, v in token_length.items()
    if k == mode(list(token_length.keys()))
}
tokens_per_chunk = multimode(list(token_length.keys()))

std = stdev(token_length.keys())

print("=" * 100)
print(
    f"mode of token length per chunk : \n {"-"*100} \n length: {next(iter(most_common.keys()))}      count: {next(iter(most_common.values()))} \n out of {len(grouped)}, which is {int(next(iter(most_common.values())))/len(grouped):.2%}"
)
print("=" * 100)
print(f"multimode of token lengths : \n {"-"*100} \n {tokens_per_chunk}")
print("=" * 100)
print(f"stdev : \n {"-"*100} \n {std}")
