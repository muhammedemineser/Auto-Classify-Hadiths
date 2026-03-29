import re
import random as ra
from statistics import mode, multimode

seq = 1
init_no_id = 11273
grouped = {}
path = "/home/mo/desk/apps/classify/chunks_with_most_isnad_elements.xml"
with open(path) as f:
    doc = f.readlines()
    for line in doc:
        match = re.match(r"^(\d+)?\|", line)
        if match:
            if match.group(1) is not None:
                match = int(match.group(1))
            else:
                match = init_no_id
                init_no_id += 1
            seq = match
            grouped[seq] = [line]
        else:
            grouped[seq].append(line)
isnad_counter = {}
isnad_elements = []
for k, v in grouped.items():
    to_str = "".join(v)
    res = [m.start() for m in re.finditer("<isnad>", to_str)]

    for tok in v:
        if "<isnad>" in tok:
            if k not in isnad_counter:
                isnad_counter[k] = 1
            else:
                isnad_counter[k] += 1

sorted_isnad_freqs = sorted(
    isnad_counter.items(), key=lambda item: item[1], reverse=True
)
only_count = []
for el in sorted_isnad_freqs:
    only_count.append(el[1])

print(only_count)
print(mode(only_count))
print(multimode(only_count))

times = {}  # number: count
del el
for i, el in enumerate(only_count):
    if el not in times:
        times[el] = 1
    elif el in times:
        times[el] += 1
print(times)
