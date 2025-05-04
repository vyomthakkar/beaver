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
from llm import gpt


load_dotenv()


input_schema_path = 'testcases/citations.json'
# input_schema_path = 'schema_chunk_5.json'
input_text_path = 'testcases/transformers.bib'


def extract_document(file_path):
    print(f"Extracting document from {file_path}")
    client = genai.Client()
    model = "gemini-2.0-flash"

    file_ref = client.files.upload(file=file_path, config=types.UploadFileConfig(mime_type="text/plain"))

    extract_document_prompt = """
    Review the provided file content. Extract the relevant information based on the
    JSON schema structure expected in the output format configuration.
    Ensure the output strictly adheres to the schema.
    """

    # response = client.models.generate_content(model=model, contents="Hello, world!")
    # print(response.text)

    result = client.models.generate_content(
        model=model,
        contents=[file_ref, extract_document_prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json", 
            response_schema=convert_schema_to_pydantic(input_schema_path)
        ),
    )
    
    print(convert_schema_to_pydantic(input_schema_path))

    print(result.text)
    
    # Parse the text response into JSON
    try:
        json_result = json.loads(result.text)
        return json_result
    except json.JSONDecodeError:
        # If parsing fails, return a structured error response
        return {"error": "Failed to parse response as JSON", "raw_text": result.text}
    
    
    
def extract_document_naive(file_path):
    print(f"Extracting document from {file_path}")
    client = genai.Client()
    model = "gemini-2.0-flash"

    file_ref = client.files.upload(file=file_path, config=types.UploadFileConfig(mime_type="text/plain"))

    extract_document_prompt = f"""
    Review the provided file content. Extract the relevant information based on the
    JSON schema structure expected in the output format configuration.
    Ensure the output strictly adheres to the schema.
    
    This is the JSON schema:
    {convert_schema_to_pydantic(input_schema_path)}
    """

    # response = client.models.generate_content(model=model, contents="Hello, world!")
    # print(response.text)

    result = client.models.generate_content(
        model=model,
        contents=[file_ref, extract_document_prompt],
    )

    print(result.text)
    
    # Parse the text response into JSON
    try:
        json_result = json.loads(result.text)
        return json_result
    except json.JSONDecodeError:
        # If parsing fails, return a structured error response
        return {"error": "Failed to parse response as JSON", "raw_text": result.text}
    
    
def convert_schema_to_pydantic(schema_path):
    with open(schema_path, 'r') as file:
        schema = json.load(file)
        
    # prompt = f"""
    # Convert the following JSON schema into a Pydantic model that can be used for structured output from a LLM:
    # {schema}
    
    # The output should be a valid Pydantic model definition that can be used in a Python script.
    # Only output the Pydantic model definition, nothing else.
    # """
    
    # return gpt(prompt)
    
    return schema
    
# print(convert_schema_to_pydantic(input_schema_path))
# extract_document(input_text_path)
extract_document_naive(input_text_path)