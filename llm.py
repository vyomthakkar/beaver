import os
from openai import OpenAI
from dotenv import load_dotenv

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