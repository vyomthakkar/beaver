import json
import subprocess
import importlib.util
import os
# Import pydantic explicitly to check type later if needed
import pydantic
from google import genai
from google.genai import types
from dotenv import load_dotenv


load_dotenv()

# --- Configuration ---
input_schema_path = 'testcases/citations.json'
input_text_path = 'testcases/transformers.bib'
generated_code_path = "citations.py"
model_name = "gemini-2.0-flash" # Changed to 1.5 flash

# # --- Generate Pydantic Model ---
# print(f"Generating Pydantic model from {input_schema_path}...")
# # (Keep the subprocess.run call and error handling as in the previous corrected version)
# try:
#     subprocess.run([
#         "datamodel-codegen",
#         "--input", input_schema_path,
#         "--input-file-type", "jsonschema",
#         "--output", generated_code_path,
#         "--output-model-type", "pydantic_v2.BaseModel",
#         "--class-name", "DynamicResponseModel",
#         # "--use-annotated",
#         "--use-field-description",
#     ], check=True, capture_output=True, text=True)
#     print(f"Pydantic model saved to {generated_code_path}")
# except subprocess.CalledProcessError as e:
#     print(f"Error during datamodel-codegen execution:\nStderr: {e.stderr}")
#     exit(1)
# except FileNotFoundError:
#     print("Error: 'datamodel-codegen' command not found.")
#     exit(1)
    



# # --- Dynamically Import Generated Model ---
# print("Importing dynamic model...")
# # (Keep the importlib logic and error handling as in the previous corrected version)
# try:
#     spec = importlib.util.spec_from_file_location("temp_module", generated_code_path)
#     if spec is None or spec.loader is None:
#          raise ImportError(f"Could not create spec or loader for {generated_code_path}")
#     temp_module = importlib.util.module_from_spec(spec)
#     spec.loader.exec_module(temp_module)
#     DynamicModelClass = getattr(temp_module, "DynamicResponseModel")
#     print("Dynamic model imported successfully.")

#     # ******************************************
#     # *** ADD model_rebuild() CALL HERE ***
#     # ******************************************
#     print("Rebuilding dynamic model...")
#     # Use force=True to ensure it runs even if Pydantic thinks it's unnecessary initially
#     DynamicModelClass.model_rebuild(force=True)
#     print("Dynamic model rebuilt successfully.")
#     # ******************************************

# except AttributeError:
#      print(f"Error: Class 'DynamicResponseModel' not found in {generated_code_path}.")
#      exit(1)
# except Exception as e:
#      print(f"Error importing or rebuilding dynamic model: {e}")
#      exit(1)


# --- Gemini API Call Function ---
def extract_dynamic_document(file_path, schema_model_class):
    print(f"Extracting document from {file_path} using dynamic schema")
    try:
        # Using genai.Client() as in your working code
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY")) # Configure before Client usually
        client = genai.Client()
        print("Gemini client initialized.")
    except Exception as config_error:
        print(f"Error initializing Gemini client: {config_error}")
        return {"error": f"Client initialization failed: {config_error}"}

    # --- Prepare Input Content (Using your working upload method) ---
    try:
        print(f"Uploading file: {file_path} using client.files.upload()")
        # Using the upload method user confirmed works
        file_ref = client.files.upload(
            file=file_path, # Use file_path argument passed to function
            config=types.UploadFileConfig(mime_type="text/plain") # Hardcoding for .bib example
            # Consider making mime_type dynamic if needed later
        )
        print("File upload successful.")
        file_content_for_prompt = file_ref
    except Exception as upload_error:
         print(f"Error during file upload: {upload_error}")
         return {"error": f"Error uploading file {file_path}: {upload_error}"}

    # --- Prepare Prompt ---
    extract_prompt = f"""
    Review the provided file content. Extract the relevant information based on the
    JSON schema structure expected in the output format configuration.
    Ensure the output strictly adheres to the schema.
    """

    # --- Define Generation Configuration ---
    gen_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=schema_model_class,
        # temperature=0.1 # Optional
    )
    
    gen_config = types.GenerationConfig(
        response_mime_type="application/json",
        response_schema=schema_model_class, # Pass the dynamically loaded Pydantic class
        # Optional: Adjust temperature for more deterministic output
        # temperature=0.1
    )

    # --- Make the API Call ---
    print("Calling Gemini API...")
    try:
        # Using client.models.generate_content as in your working code
        response = client.models.generate_content(
            model=model_name, # Use model_name variable
            contents=[file_content_for_prompt, extract_prompt],
            generation_config=gen_config
        )
        print("Gemini API call successful.")

        # --- Process Response (Keep previous robust version) ---
        raw_text = getattr(response, 'text', None)
        print("Raw response text:", raw_text if raw_text else "N/A")

        if not raw_text:
             if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                 return {"error": f"Request blocked: {response.prompt_feedback.block_reason}", "details": f"{response.prompt_feedback.block_reason_message}"}
             return {"error": "No text content received from API."}

        try:
            json_result = json.loads(raw_text)
            print("Successfully parsed JSON from response text.")
            return json_result
        except json.JSONDecodeError as decode_error:
             print(f"JSONDecodeError from response text: {decode_error}")
             return {"error": "Failed to parse API response as JSON", "raw_text": raw_text}

    except Exception as e:
        print(f"Error during Gemini API call or processing: {e}")
        raw_text_on_error = getattr(response, 'text', 'N/A') if 'response' in locals() else 'N/A'
        return {"error": str(e), "raw_text": raw_text_on_error}


# --- Main Execution ---
print("--- Starting Extraction Process ---")
# final_result = extract_dynamic_document(input_text_path, DynamicModelClass)
final_result = extract_dynamic_document(input_text_path,input_schema_path)
print("\n--- Final Result ---")
if isinstance(final_result, dict) or isinstance(final_result, list):
    print(json.dumps(final_result, indent=2))
else:
    print(final_result)

# Optional: Clean up
# try:
#     os.remove(generated_code_path)
#     print(f"\nCleaned up {generated_code_path}")
# except OSError as e:
#     print(f"\nWarning: Could not clean up {generated_code_path}: {e}")