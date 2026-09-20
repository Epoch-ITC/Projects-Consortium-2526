import json

path_file = "outputs/path_with_bio.json"   # or whichever you're using

data = json.load(open(path_file))

print("\nRAW JSON CONTENT:\n")
print(data[:10], "...")   # print first 10 entries

print("\nType of elements:")
for i,x in enumerate(data[:10]):
    print(i, type(x), x)
