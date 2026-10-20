import time
from datetime import date
from typing import Optional
from google import genai
from google.genai import types
import zahra_tools as t

MODEL = "gemini-3.8-flash"
client = genai.Client(api_key=open("gemini_key.txt").read().strip())


def _run(fn, *args):
    try:
        t.LAST_CONFIRMED = False
        fn(*args)
        return "Saved." if t.LAST_CONFIRMED else "Cancelled by the user. Nothing was changed."
    except Exception as e:
        return f"Error: {e}"


def _run_delete(fn, *args):
    try:
        t.LAST_CONFIRMED = False
        note = fn(*args)
        if note:
            return note
        return "Deleted." if t.LAST_CONFIRMED else "Cancelled by the user. Nothing was deleted."
    except Exception as e:
        return f"Error: {e}"


def mark_attendance(student: str, pre_req: bool, session: bool, post_req: bool,
                    day: Optional[str] = None) -> str:
    """Record or correct a student's attendance for one day.
    pre_req, session, post_req say whether each part was attended.
    day is YYYY-MM-DD; leave empty for today."""
    return _run(t.mark_attendance, student, pre_req, session, post_req, day)


def attendance_percent(student: str) -> str:
    """Get a student's overall attendance percentage."""
    try:
        return t.attendance_percent(student)
    except Exception as e:
        return f"Error: {e}"


def add_score(student: str, score: float, max_score: float,
              subject: str = "", notes: str = "", day: Optional[str] = None) -> str:
    """Add a test score. day is YYYY-MM-DD; leave empty for today."""
    return _run(t.add_score, student, score, max_score, subject, notes, day)


def add_material(batch: str, title: str, link: str) -> str:
    """Add a learning material link to every student in a batch."""
    return _run(t.add_material, batch, title, link)


def delete_attendance(student: str, day: str) -> str:
    """Delete a student's attendance entry for one day (YYYY-MM-DD)."""
    return _run_delete(t.delete_attendance, student, day)


def delete_score(student: str, day: str, subject: str = "") -> str:
    """Delete a student's score from one day (YYYY-MM-DD). subject narrows it down."""
    return _run_delete(t.delete_score, student, day, subject)


def delete_material(batch: str, title: str) -> str:
    """Delete a material, matched by its exact title, from every student in a batch."""
    return _run_delete(t.delete_material, batch, title)


SYSTEM = f"""You are Zahra, the admin assistant for CoRadix Academy. Today is {date.today()}.
Use your tools to do what the academy owner asks. Rules:
- Attendance has three parts: pre-req, live session, post-req. "Fully present" = all three.
  "Present except pre-reqs" = pre_req false, others true. Same idea for post-reqs. "Absent" = all false.
- Turn words like "yesterday" into YYYY-MM-DD dates using today's date.
- If anything is unclear (for example "late", or two students match), ask one short question. Never guess.
- Only say something was saved if the tool result says "Saved.".
- Only say something was deleted if the tool result says "Deleted.".
- If a tool result says cancelled, say nothing changed.
- Keep replies short and plain."""

chat = client.chats.create(
    model=MODEL,
    config=types.GenerateContentConfig(
        system_instruction=SYSTEM,
        tools=[mark_attendance, attendance_percent, add_score, add_material,
               delete_attendance, delete_score, delete_material],
    ),
)


def ask(msg):
    for attempt in range(5):
        try:
            return chat.send_message(msg).text
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                print("(Free limit reached, waiting 30 seconds...)")
                time.sleep(30)
                continue
            if "503" in err or "UNAVAILABLE" in err:
                print("(Gemini is busy, retrying...)")
                time.sleep(5 * (attempt + 1))
                continue
            return "Zahra had a problem: " + err[:400]
    return "Still limited or busy. Wait a minute and try again."

if __name__ == "__main__":
    print("Zahra is ready. Type your request below.")
    print("Type 'exit' or 'quit' to close Zahra. Press Ctrl+C to stop.\n")

    while True:
        try:
            user_message = input("You: ").strip()

            if not user_message:
                continue

            if user_message.lower() in {"exit", "quit"}:
                print("Zahra: Goodbye!")
                break

            response = ask(user_message)
            print(f"\nZahra: {response}\n")

        except (KeyboardInterrupt, EOFError):
            print("\nZahra: Goodbye!")
            break
        except Exception as e:
            print(f"\nZahra: Something went wrong: {e}\n")
