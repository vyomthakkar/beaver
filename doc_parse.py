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
from llm import gpt_file


load_dotenv()
    
    
def extract_document(file_path, schema):
    print(f"Extracting document from {file_path}")

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

    result = gpt_file(extract_document_prompt, file_path)
    
    return result
    
    
    
def convert_schema_to_json(schema_path):
    with open(schema_path, 'r') as file:
        schema = json.load(file)
    
    return schema
    
