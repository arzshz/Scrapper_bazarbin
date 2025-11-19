from pymongo import MongoClient
from datetime import timedelta

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["bazarbin_data"]
collection = db["prices"]

# Fetch all documents sorted by timestamp
docs = list(collection.find({"timestamp": {"$exists": True}}).sort("timestamp", 1))

to_delete = []
prev_ts = None

for doc in docs:
    ts = doc["timestamp"]
    if prev_ts is not None:
        # Check difference
        if (ts - prev_ts) < timedelta(minutes=1):
            to_delete.append(doc["_id"])
    prev_ts = ts

# Remove documents with too-close timestamps
if to_delete:
    result = collection.delete_many({"_id": {"$in": to_delete}})
    print(f"Deleted {result.deleted_count} documents.")
else:
    print("No documents to delete.")
