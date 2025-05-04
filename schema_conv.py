from google import genai
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional
from enum import Enum
import json
from google.genai import types
import os
import time
import concurrent.futures
from llm import gpt_file, gpt


load_dotenv()


# input_schema_path = 'testcases/citations.json'
input_schema_path = 'schema_chunk_5.json'
input_text_path = 'testcases/transformers.bib'
    
    
    
def extract_document(file_path, schema):
    print(f"Extracting document from {file_path}")
    # client = genai.Client()
    # model = "gemini-2.0-flash"
    # model="gemini-2.5-flash-preview-04-17"

    # file_ref = client.files.upload(file=file_path, config=types.UploadFileConfig(mime_type="text/plain"))

    extract_document_prompt = f"""
    Review the provided file content. Extract the relevant information based on the
    JSON schema structure expected in the output format configuration.
    Ensure the output strictly adheres to the schema. 
    Think carefully about the schema and the content of the file and extract the relevant information correctly.
    Output should be in JSON format only.
    If certain information is not present in the file, then do not include it in the output. Strictly only include information that is present in the file.
    If you are not sure about a particular extracted information, flag it as "needs_review" as a boolean value as a key in the output and provide a reason as a string value as a key in the output.
    
    This is the JSON schema:
    {schema}
    """

    # result = client.models.generate_content(
    #     model=model,
    #     contents=[file_ref, extract_document_prompt],
    #     # temperature=0.0,
    #     # config={'response_mime_type': 'application/json', 'temperature': 0.0}
    #     config=types.GenerateContentConfig(
    #         response_mime_type="application/json",
    #         temperature=0.0
    #     )
    # )
    # print("-"*100)
    # print(result.text)
    # print("-"*100)
    
    print("-"*100)
    result = gpt_file(extract_document_prompt, file_path)
    print(result)
    print("-"*100)
    
    return result
    
    # Parse the text response into JSON
    try:
        json_result = json.loads(result.text)
        return json_result
    except json.JSONDecodeError:
        # If parsing fails, return a structured error response
        return {"error": "Failed to parse response as JSON", "raw_text": result.text}
    
    
def convert_schema_to_json(schema_path):
    with open(schema_path, 'r') as file:
        schema = json.load(file)
    
    return schema
    
# print(convert_schema_to_pydantic(input_schema_path))
# extract_document(input_text_path, convert_schema_to_json(input_schema_path))
# extract_document_naive(input_text_path)