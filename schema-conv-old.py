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

# --- Generate Pydantic Model ---
print(f"Generating Pydantic model from {input_schema_path}...")
try:
    subprocess.run([
        "datamodel-codegen",
        "--input", input_schema_path,
        "--input-file-type", "jsonschema",
        "--output", generated_code_path,
        "--output-model-type", "pydantic_v2.BaseModel",
        "--class-name", "DynamicResponseModel",
        "--use-annotated", # Often helpful for newer Pydantic versions
        "--use-field-description", # Include descriptions
    ], check=True, capture_output=True, text=True) # Added capture_output/text for better error visibility if needed
    print(f"Pydantic model saved to {generated_code_path}")
except subprocess.CalledProcessError as e:
    print(f"Error during datamodel-codegen execution:")
    print(f"Return code: {e.returncode}")
    print(f"Stderr: {e.stderr}")
    print(f"Stdout: {e.stdout}")
    exit(1) # Exit if model generation fails
except FileNotFoundError:
    print("Error: 'datamodel-codegen' command not found. Is it installed and in your PATH?")
    exit(1)

# --- Dynamically Import Generated Model ---
print("Importing dynamic model...")
try:
    spec = importlib.util.spec_from_file_location("temp_module", generated_code_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create spec or loader for {generated_code_path}")
    temp_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(temp_module)
    DynamicModelClass = getattr(temp_module, "DynamicResponseModel") # Get the generated class
    print("Dynamic model imported successfully.")
except AttributeError:
     print(f"Error: Class 'DynamicResponseModel' not found in {generated_code_path}. Check --class-name argument.")
     exit(1)
except Exception as e:
     print(f"Error importing dynamic model: {e}")
     exit(1)

# --- Gemini API Call Function ---
def extract_dynamic_document(file_path, schema_model_class):
    print(f"Attempting extraction from {file_path} using dynamic schema...")
    try:
        # Configure the client (it should automatically find GOOGLE_API_KEY from env)
        # REMOVE OR COMMENT OUT THIS LINE:
        # genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

        # Initialize the model client - it will pick up the key from the environment
        client = genai.GenerativeModel(model_name=model_name)
        print("Gemini client initialized successfully.") # Add confirmation
    except Exception as config_error:
        print(f"Error initializing Gemini client: {config_error}") # Changed error message
        return {"error": f"Client initialization failed: {config_error}"}

    # --- Prepare Input Content (Upload or Read Text) ---
    file_content_for_prompt = None
    try:
        print(f"Attempting to upload file: {file_path} using genai.upload_file()")
        # This function handles mime type detection automatically.
        file_ref = genai.upload_file(path=file_path)
        file_content_for_prompt = file_ref # Use the reference if upload succeeds
        print("File upload successful.")
    except ValueError as e:
        if "Could not determine the mimetype" in str(e) or "Unsupported MIME type" in str(e):
            print(f"genai.upload_file failed: {e}. Reading file as text instead.")
            try:
                # Fallback for unknown types: read as raw text
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_text_content = f.read()
                file_content_for_prompt = file_text_content # Use the raw text
                print(f"Successfully read file content as text ({len(file_text_content)} chars).")
            except Exception as read_error:
                print(f"Failed to read file {file_path} as text: {read_error}")
                return {"error": f"Failed to process file {file_path}: {read_error}"}
        else:
            # Re-raise other ValueErrors from upload_file
            print(f"ValueError during file upload: {e}")
            return {"error": f"Error uploading file {file_path}: {e}"}
    except Exception as upload_error:
         print(f"Unexpected error during file upload: {upload_error}")
         # Print traceback for unexpected errors
         # traceback.print_exc()
         return {"error": f"Unexpected error uploading file {file_path}: {upload_error}"}

    if file_content_for_prompt is None:
         return {"error": f"Could not prepare content from file {file_path}"}

    # --- Prepare Prompt ---
    # Keep the prompt simple, let the schema guide the structure
    extract_prompt = """
    Review the provided file content. Extract the relevant information based on the
    JSON schema structure expected in the output format configuration.
    Ensure the output strictly adheres to the schema.
    """

    # --- Define Generation Configuration ---
    gen_config = types.GenerationConfig(
        response_mime_type="application/json",
        response_schema=schema_model_class, # Pass the dynamically loaded Pydantic class
        # Optional: Adjust temperature for more deterministic output
        # temperature=0.1
    )

    # --- Make the API Call ---
    print("Calling Gemini API...")
    try:
        # Use the client created from GenerativeModel
        response = client.generate_content(
            # Pass file reference OR raw text + the prompt text in a list
            contents=[file_content_for_prompt, extract_prompt],
            generation_config=gen_config
        )
        print("Gemini API call successful.")

        # --- Process Response ---
        raw_text = getattr(response, 'text', None)
        print("Raw response text:", raw_text if raw_text else "N/A")

        if not raw_text:
             # Check for blocked content or other issues
             print(f"Warning: No text found in response.")
             # print(f"Prompt Feedback: {getattr(response, 'prompt_feedback', 'N/A')}")
             # print(f"Finish Reason: {getattr(response.candidates[0], 'finish_reason', 'N/A') if response.candidates else 'N/A'}")
             if response.prompt_feedback.block_reason:
                 return {"error": f"Request blocked: {response.prompt_feedback.block_reason}", "details": f"{response.prompt_feedback.block_reason_message}"}
             return {"error": "No text content received from API."}

        # Parse the JSON from the response text
        try:
            json_result = json.loads(raw_text)
            print("Successfully parsed JSON from response text.")
            # Optional: Add validation against the original JSON schema here if desired
            # from jsonschema import validate
            # with open(input_schema_path, 'r') as f:
            #     original_schema_dict = json.load(f)
            # try:
            #     validate(instance=json_result, schema=original_schema_dict)
            #     print("JSON Schema validation successful!")
            # except Exception as validation_error:
            #     print(f"Warning: JSON Schema validation failed: {validation_error}")
            #     # Decide if validation failure is an error or just a warning
            return json_result # Return even if validation fails for now
        except json.JSONDecodeError as decode_error:
             print(f"JSONDecodeError from response text: {decode_error}")
             return {"error": "Failed to parse API response as JSON", "raw_text": raw_text}

    except Exception as e:
        print(f"Error during Gemini API call or processing: {e}")
        # Print traceback for unexpected errors during the API call phase
        # traceback.print_exc()
        raw_text_on_error = getattr(response, 'text', 'N/A') if 'response' in locals() else 'N/A'
        return {"error": str(e), "raw_text": raw_text_on_error}


# --- Main Execution ---
print("--- Starting Extraction Process ---")
final_result = extract_dynamic_document(input_text_path, DynamicModelClass)
print("\n--- Final Result ---")
# Pretty print the JSON result
if isinstance(final_result, dict) or isinstance(final_result, list):
    print(json.dumps(final_result, indent=2))
else:
    print(final_result) # Print as is if it's not dict/list (e.g., an error string)


# Optional: Clean up the generated file
# try:
#     os.remove(generated_code_path)
#     print(f"\nCleaned up {generated_code_path}")
# except OSError as e:
#     print(f"\nWarning: Could not clean up {generated_code_path}: {e}")