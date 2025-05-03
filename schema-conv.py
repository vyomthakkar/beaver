import json
import subprocess
import importlib.util
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv


load_dotenv()



input_schema_path = 'testcases/citations.json'
input_text_path = 'testcases/transformers.bib'
generated_code_path = "citations.py"
model_name = "gemini-2.0-flash"

subprocess.run([
    "datamodel-codegen",
    "--input", input_schema_path,
    "--input-file-type", "jsonschema",
    "--output", generated_code_path,
    "--output-model-type", "pydantic_v2.BaseModel", # Or pydantic_v1 if needed
    "--class-name", "DynamicResponseModel" # Or derive dynamically
], check=True)

spec = importlib.util.spec_from_file_location("temp_module", generated_code_path)
temp_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(temp_module)
DynamicModelClass = getattr(temp_module, "DynamicResponseModel") # Get the generated class

# --- Gemini API Call ---
def extract_dynamic_document(file_path, schema_model_class):
    print(f"Extracting document from {file_path} using dynamic schema")
    client = genai.Client()
    model = "gemini-2.0-flash" # Or whichever model supports the schema feature well

    # file_ref = client.files.upload(file=file_path)
    # Determine the appropriate mime type (safest is often text/plain for .bib)
    # You could add more sophisticated logic here if needed for other file types
    file_mime_type = "text/plain"
    if file_path.lower().endswith(".pdf"):
        file_mime_type = "application/pdf"
    # Add elif for other known types like images if you plan to support them

    print(f"Uploading file: {file_path} with MIME type: {file_mime_type}") # Added print for debugging
    file_ref = client.files.upload(
        file=file_path,
        mime_type=file_mime_type  # <-- Add this argument
    )

    # You might need to adjust the prompt to be more generic
    # or potentially include parts of the schema description in the prompt
    extract_prompt = f"""
    Input is a file. Your job is to extract information according
    to the provided JSON schema structure. Find the relevant details
    in the text and format them strictly according to the schema.
    Input file content is provided first.
    """

    try:
        result = client.models.generate_content(
            model=model,
            contents=[file_ref, extract_prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema_model_class # Pass the dynamically loaded class
            ),
            # Consider adding generation_config like temperature=0 for more deterministic JSON
        )
        print(result.text)
        json_result = json.loads(result.text)
        # Optional: Validate the result against the original input_schema_path using jsonschema lib
        return json_result
    except Exception as e:
        print(f"Error during Gemini call or JSON parsing: {e}")
        # Handle potential errors from API or JSON loading
        return {"error": str(e)}


# --- Main Execution ---
final_result = extract_dynamic_document(input_text_path, DynamicModelClass)
print(final_result)


# print(DynamicModelClass)

# Clean up the generated file
# os.remove(generated_code_path)