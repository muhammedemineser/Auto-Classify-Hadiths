import re

with open("chunks_with_most_isnad_elements2.xml") as f:
    doc = list(f.readlines())
    print(doc)
    for line in doc:
        for match in re.finditer(r"^(\d+)?\|", line):
            doc = [s.replace(match.group(), "") for s in doc]
            pass
print(doc)
