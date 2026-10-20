import firebase_admin
from datetime import date
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

firebase_admin.initialize_app(credentials.Certificate("serviceAccountKey.json"))
db = firestore.client()

WEIGHTS = {"preReq": 0.25, "session": 0.5, "postReq": 0.25}
DEL = "DELETE this? This cannot be undone (y/n): "

LAST_CONFIRMED = False


def confirm(msg, prompt="Save this? (y/n): "):
    global LAST_CONFIRMED
    print("\n" + msg)
    LAST_CONFIRMED = input(prompt).strip().lower() == "y"
    return LAST_CONFIRMED


def one_student(query):
    q = query.lower().strip()
    students = list(db.collection("students").stream())
    exact = [d for d in students
             if q == d.to_dict()["name"].lower() or q == d.to_dict()["studentId"].lower()]
    if len(exact) == 1:
        return exact[0]
    partial = [d for d in students if q in d.to_dict()["name"].lower()]
    if len(partial) != 1:
        raise ValueError(f"'{query}' matched {len(partial)} students. Be more specific.")
    return partial[0]


def mark_attendance(query, pre, session, post, day=None):
    s = one_student(query)
    day = day or str(date.today())
    data = {"date": day, "preReq": pre, "session": session, "postReq": post,
            "status": "Present" if session else "Absent"}
    col = s.reference.collection("attendance")
    existing = list(col.where(filter=FieldFilter("date", "==", day)).stream())
    verb = "UPDATE" if existing else "ADD"
    if confirm(f"{verb} attendance for {s.to_dict()['name']}: {data}"):
        if existing:
            existing[0].reference.set(data)
        else:
            col.add(data)
        print("Saved.")


def attendance_percent(query):
    s = one_student(query)
    total, n = 0, 0
    for a in s.reference.collection("attendance").stream():
        d = a.to_dict()
        if "session" not in d:  # old entry: Present = all parts, Absent = none
            ok = d.get("status") == "Present"
            d = {"preReq": ok, "session": ok, "postReq": ok}
        total += sum(w for k, w in WEIGHTS.items() if d.get(k))
        n += 1
    name = s.to_dict()["name"]
    return f"{name}: {round(total / n * 100, 1)}% over {n} sessions" if n else f"{name}: no records"


def add_score(query, score, max_score, subject="", notes="", day=None):
    s = one_student(query)
    data = {"date": day or str(date.today()), "score": score, "max": max_score,
            "rating": round(score / max_score * 10, 2), "subject": subject, "notes": notes}
    if confirm(f"ADD score for {s.to_dict()['name']}: {data}"):
        s.reference.collection("scores").add(data)
        print("Saved.")


def add_material(batch, title, link):
    students = [d for d in db.collection("students").stream()
                if d.to_dict()["batchName"] == str(batch)]
    names = ", ".join(d.to_dict()["name"] for d in students)
    if students and confirm(f"ADD material '{title}' to {len(students)} students in Batch {batch}: {names}\n{link}"):
        for d in students:
            d.reference.collection("materials").add({"title": title, "link": link})
        print("Saved.")


def delete_attendance(query, day):
    s = one_student(query)
    found = list(s.reference.collection("attendance")
                 .where(filter=FieldFilter("date", "==", day)).stream())
    if not found:
        return f"No attendance entry on {day}."
    if confirm(f"DELETE attendance for {s.to_dict()['name']} on {day}: {found[0].to_dict()}", DEL):
        for f in found:
            f.reference.delete()
        print("Deleted.")


def delete_score(query, day, subject=""):
    s = one_student(query)
    found = [d for d in s.reference.collection("scores").stream()
             if d.to_dict().get("date") == day
             and subject.lower() in d.to_dict().get("subject", "").lower()]
    if not found:
        return "No matching score found."
    if len(found) > 1:
        subjects = "; ".join(f.to_dict().get("subject", "") for f in found)
        return f"{len(found)} scores match ({subjects}). Ask the user which subject."
    if confirm(f"DELETE score for {s.to_dict()['name']}: {found[0].to_dict()}", DEL):
        found[0].reference.delete()
        print("Deleted.")


def delete_material(batch, title):
    found = []
    for st in db.collection("students").stream():
        if st.to_dict()["batchName"] == str(batch):
            found += [m for m in st.reference.collection("materials").stream()
                      if m.to_dict().get("title") == title]
    if not found:
        return f"No material titled '{title}' in Batch {batch}."
    if confirm(f"DELETE material '{title}' ({len(found)} copies) from Batch {batch}", DEL):
        for m in found:
            m.reference.delete()
        print("Deleted.")
