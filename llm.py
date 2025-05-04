import os
from openai import OpenAI
from dotenv import load_dotenv
import mimetypes
import json


load_dotenv()

def gpt(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=8000,
        temperature=0.0
    )
    return response.choices[0].message.content


# def gpt_file(prompt: str, file_path: str) -> str:
#     api_key = os.getenv("OPENAI_API_KEY")
#     client = OpenAI(api_key=api_key)
    
#     mime_type, _ = mimetypes.guess_type(file_path)
#     mime_type = mime_type or ""
    
#     file = client.files.create(
#         file=open(file_path, "rb"),
#         purpose="user_data"
#     )
#     response = client.chat.completions.create(
#         model="gpt-4.1",
#             messages=[
#                 {
#                     "role": "user",
#                     "content": [
#                         {
#                             "type": "file",
#                             "file": {
#                                 "file_id": file.id,
#                             }
#                         },
#                         {
#                             "type": "text",
#                             "text": prompt,
#                         },
#                     ]
#                 }
#             ],
#             # max_tokens=8000,
#             temperature=0.0
#     )
#     return response.choices[0].message.content

# def gpt_file(prompt: str, file_path: str) -> str:
#     api_key = os.getenv("OPENAI_API_KEY")
#     client = OpenAI(api_key=api_key)

#     # 1. Guess MIME type from file extension
#     mime_type, _ = mimetypes.guess_type(file_path)
#     mime_type = mime_type or ""

#     messages = []

#     # 2. If it's a PDF, upload as a file
#     if mime_type == "application/pdf":
#         with open(file_path, "rb") as f:
#             uploaded = client.files.create(file=f, purpose="user_data")
#         messages.append({
#             "type": "file",
#             "file": { "file_id": uploaded.id }
#         })

#     # 3. Otherwise, assume it's text‐readable and include inline
#     else:
#         # You might want to limit very large files or chunk them to avoid token limits
#         with open(file_path, "r", encoding="utf-8") as f:
#             text = f.read()
#         messages.append({
#             "type": "text",
#             "text": text
#         })

#     # 4. Finally, append the user’s prompt
#     messages.append({
#         "type": "text",
#         "text": prompt
#     })

#     # 5. Call the chat completion
#     response = client.chat.completions.create(
#         model="gpt-4.1",
#         messages=[{"role":"user","content": messages}],
#         temperature=0.0,
#     )

#     return response.choices[0].message.content


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
