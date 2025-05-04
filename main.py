import fastapi
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import tempfile
import shutil
import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from typing import List, Dict, Any
import tiktoken



from schema_conv import extract_document, convert_schema_to_json
from schema_chunk_graph import create_schema_chunks, get_token_count




def format(input_file, schema_json):
    # schema_json = convert_schema_to_json(schema)
    generated_chunks = create_schema_chunks(
        schema_json,
        tokenizer_name="cl100k_base",
        threshold=10000,
        sort_props=True
    )
    
    
    # # --- Output Results (Optional) ---
    # if generated_chunks:
    #     print(f"\n--- Generated {len(generated_chunks)} Schema Chunks ---")
    #     for i, chunk in enumerate(generated_chunks):
    #         chunk_props = list(chunk.get('properties', {}).keys())
    #         num_defs = len(chunk.get('definitions', {}))
    #         # Optional: Estimate token count of the final generated chunk itself
    #         try:
    #             chunk_tokenizer = tiktoken.get_encoding("cl100k_base")
    #             chunk_token_count = get_token_count(chunk, chunk_tokenizer)
    #             print(f"Chunk {i+1} (Properties: {chunk_props}) "
    #                 f"({num_defs} definitions) "
    #                 f"(Est. Chunk Tokens: {chunk_token_count})")
    #         except Exception as e:
    #             print(f"Chunk {i+1} (Properties: {chunk_props}) ({num_defs} definitions) - Error estimating chunk tokens: {e}")

    #         # Optional: Save each chunk to a file
    #         with open(f'schema_chunk_{i+1}.json', 'w') as f:
    #             json.dump(chunk, f, indent=2)
    # else:
    #     print("No schema chunks were generated.")
    
    chunked_output = []
    
    # print(generated_chunks[0])
    # return
    
    for chunk in generated_chunks:
        # print("-"*100)
        # print("schema chunk: ", chunk['properties'].keys())
        # print("-"*100)
        chunked_output.append(extract_document(input_file, chunk))
        
    print(chunked_output)
    print(len(chunked_output))
    
    return chunked_output



# --- FastAPI Application ---
app = FastAPI(
    title="Document Formatting API",
    description="Uploads an input file and a JSON schema file, then processes the document based on the schema.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
        
@app.post("/format/", response_model=List[Dict[str, Any]])
async def create_format_job(
    input_file: UploadFile = File(..., description="The input document file (any format)."),
    schema_file: UploadFile = File(..., description="The schema definition file (.json).")
):
    """
    Accepts an input file and a schema file, formats the document,
    and returns the chunked output.
    """
    # Validate schema file type
    if not schema_file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Invalid schema file type. Please upload a .json file.")

    # Create a temporary directory to store the uploaded file
    temp_dir = tempfile.mkdtemp()
    input_file_path = os.path.join(temp_dir, input_file.filename)

    try:
        # 1. Save the uploaded input file temporarily
        try:
            with open(input_file_path, "wb") as buffer:
                shutil.copyfileobj(input_file.file, buffer)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save input file: {e}")
        finally:
            await input_file.close() # Close the upload file object

        # 2. Read and parse the uploaded schema file
        try:
            schema_content = await schema_file.read()
            schema_json = json.loads(schema_content)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format in schema file.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read or parse schema file: {e}")
        finally:
            await schema_file.close() # Close the upload file object

        # 3. Call the core formatting function
        try:
            results = format(input_file_path, schema_json)
            if results is None: # Handle case where format_documents might return None unexpectedly
                 raise HTTPException(status_code=500, detail="Formatting function returned an unexpected None value.")
            return results
        except ValueError as ve: # Catch specific errors if needed
             raise HTTPException(status_code=400, detail=f"Formatting error: {ve}")
        except Exception as e:
            # Log the exception for debugging
            print(f"Error during formatting: {e}")
            # Raise a generic server error for the client
            raise HTTPException(status_code=500, detail=f"An internal error occurred during document formatting: {e}")

    finally:
        # 4. Clean up: Remove the temporary directory and its contents
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Welcome to the beaver API."}

# --- Main execution block ---
if __name__ == "__main__":
    # Run the FastAPI app using uvicorn
    # Host '0.0.0.0' makes it accessible on your network
    # Reload=True is useful for development, automatically restarts on code changes
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    # For production, consider using a more robust server setup (e.g., gunicorn with uvicorn workers)
    # uvicorn.run(app, host="127.0.0.1", port=8000) # Simpler run without reload



# extract_document('testcases/transformers.bib', convert_schema_to_json('schema_chunk_5.json'))
# format('testcases/transformers.bib', 'testcases/citations.json')