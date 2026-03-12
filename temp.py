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


print(char_idx_to_token_idx("ich fahre gerne fahrrad", [2, 18y]))
print(len("ich fahre gerne fahrrad"))
