import os
from openai import OpenAI
from dotenv import load_dotenv
import mimetypes
import json


load_dotenv()


def gpt_file(prompt: str, file_path: str) -> dict:
    api_key = os.getenv("OPENAI_API_KEY")
    client  = OpenAI(api_key=api_key)

    # 1. Guess MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or ""

    user_payload = []

    # 2. Upload PDF if needed, else inline text
    if mime_type == "application/pdf":
        with open(file_path, "rb") as f:
            uploaded = client.files.create(file=f, purpose="user_data")
        user_payload.append({
            "type": "file",
            "file": { "file_id": uploaded.id }
        })
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        user_payload.append({
            "type": "text",
            "text": text
        })

    # 3. Append the actual prompt
    user_payload.append({
        "type": "text",
        "text": prompt
    })

    # 4. Send chat completion with a system instruction
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[
            {"role": "system", "content": "You are a JSON generator.  Always reply with exactly one JSON object, no extra text."},
            {"role": "user",   "content": user_payload}
        ],
        temperature=0.0,
    )

    # 5. Parse and return as Python dict
    raw = response.choices[0].message.content
    return json.loads(raw)
