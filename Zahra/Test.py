import firebase_admin
from firebase_admin import credentials, firestore

firebase_admin.initialize_app(credentials.Certificate("serviceAccountKey.json"))
db = firestore.client()

for doc in db.collection("students").stream():
    d = doc.to_dict()
    print(d["studentId"], d["name"], "Batch", d["batchName"])
