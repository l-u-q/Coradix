from google import genai

client = genai.Client(api_key=open("gemini_key.txt").read().strip())
for m in client.models.list():
    if "generateContent" in (m.supported_actions or []):
        print(m.name)