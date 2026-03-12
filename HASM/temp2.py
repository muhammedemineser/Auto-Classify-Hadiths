def char_idx_to_token_idx(tokens: str, char_idx: list) -> list:
    indexes = []
    for idx in char_idx:
        pos = 0
        for i, token in enumerate(tokens.split()):
            pos += len(token) + 1
            if idx < pos:
                indexes.append(i)
                break
    return indexes


x = char_idx_to_token_idx("Ich laufe zur Schule am morgen", [2, 12, 15])
print(x)
print(None == None)
