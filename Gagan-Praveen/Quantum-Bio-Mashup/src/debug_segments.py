import pickle

db = pickle.load(open("database/master_db.pkl", "rb"))
seg = db[0]

print("Segment object type:", type(seg))
print("\nAvailable attributes:\n", seg.__dict__)   # VERY IMPORTANT
print("\nExample segment:")

for k,v in seg.__dict__.items():
    print(f"{k}  :  {v}")

