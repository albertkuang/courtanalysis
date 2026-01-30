import json

with open('kabeer_full.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Look for 12.37 or anything close
for k, v in data.items():
    if isinstance(v, (int, float)) and 12.3 < v < 12.4:
        print(f"Match in root: {k} = {v}")
    if isinstance(v, dict):
        for sk, sv in v.items():
            if isinstance(sv, (int, float)) and 12.3 < sv < 12.4:
                print(f"Match in {k}: {sk} = {sv}")
    if isinstance(v, list):
        for item in v:
            if isinstance(item, dict):
                for sk, sv in item.items():
                    if isinstance(sv, (int, float)) and 12.3 < sv < 12.4:
                        print(f"Match in {k} list: {sk} = {sv}")

# Also check display strings
for k, v in data.items():
    if isinstance(v, str) and "12.37" in v:
        print(f"Display match: {k} = {v}")
