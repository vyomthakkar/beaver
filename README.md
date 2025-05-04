# 🦫 beaver

Schema-Driven Structured Data Extraction

beaver is designed to reliably extract structured data in JSON format from unstructured text inputs. 

A key feature of Beaver is its ability to handle **large and complex JSON schemas** that might otherwise exceed API token limits. It achieves this by intelligently decomposing the input schema into smaller, self-contained "chunks" before processing.


## 📁 Project Structure

```text
beaver/
├── .venv/              # Virtual environment directory
├── __pycache__/        # Python bytecode cache (auto-generated)
├── testcases/          # Sample files for testing
│   ├── citations.json
│   ├── ga.json
│   ├── ga.md
│   ├── resume.json
│   ├── resume.pdf
│   └── transformers.bib
├── .env                # Environment variables (OPENAI_API_KEY)
├── .gitignore          # Files/folders for Git to ignore
├── doc_parse.py        # Doc-extraction module
├── llm.py              # OpenAI API client
├── main.py             # FastAPI entry point
├── README.md           # This file
├── requirements.txt    # Dependencies
├── schema_chunk.py     # Large-schema splitter
└── testapi.py          # API tester script
```


## File Descriptions

* **`main.py`**:
    * Sets up and runs the FastAPI application using `uvicorn`.
    * Defines the `/format/` API endpoint which accepts `input_file` and `schema_file` uploads.
    * Handles temporary file storage for uploads.
    * Orchestrates the process: calls `schema_chunk.py` to split the schema, then calls `doc_parse.py` for each chunk to extract information from the input file.
    * Manages CORS (Cross-Origin Resource Sharing) middleware.
* **`doc_parse.py`**:
    * Contains the `extract_document` function.
    * Takes a file path and a single schema chunk.
    * Constructs a prompt for the LLM, instructing it to extract data based on the given schema chunk.
    * Calls the `gpt_file` function from `llm.py` to get the extraction result.
* **`schema_chunk.py`**:
    * Contains the `create_schema_chunks` function.
    * Takes a full JSON schema and splits it into smaller, manageable chunks based on estimated token count (`tiktoken`).
    * Resolves internal schema references (`$ref`) within definitions to accurately calculate token counts and ensure each chunk is self-contained with necessary definitions.
    * Aims to keep each chunk's relevant schema definition below a specified token `threshold`.
* **`llm.py`**:
    * Contains the `gpt_file` function.
    * Handles the direct interaction with the OpenAI API (GPT-4.1).
    * Loads the API key from the `.env` file.
    * Determines the input file type (e.g., PDF vs. text).
    * Uploads files to OpenAI if necessary (for formats like PDF that the model API accepts as files).
    * Sends the prompt and file reference/content to the chat completion endpoint.
    * Parses the JSON response from the LLM.
* **`testapi.py`**:
    * A simple client script using the `requests` library.
    * Sends a POST request with sample files from the `testcases/` directory to the running FastAPI application's `/format/` endpoint.
    * Prints the status code and JSON response from the API for quick testing.
* **`testcases/`**:
    * A directory containing various example input files (`.pdf`, `.bib`, `.md`) and corresponding JSON schema files (`.json`) to be used for testing the API.
* **`requirements.txt`**:
    * Lists the Python packages required to run the project (e.g., `fastapi`, `uvicorn`, `openai`, `python-dotenv`, `tiktoken`, `requests`, `python-multipart`).
* **`.env`**:
    * Stores environment variables, most importantly the `OPENAI_API_KEY`. **This file should not be committed to version control.** Create it locally.
* **`.gitignore`**:
    * Tells Git which files and directories to ignore (e.g., `.env`, `venv/`, `__pycache__/`).




## Setup and Running Instructions

1.  **Prerequisites:**
    * Python 3.8+ installed.
    * Git installed.

2.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory> # e.g., cd beaver
    ```

3.  **Create and Activate Virtual Environment (Recommended):**
    ```bash
    # Linux/macOS
    python3 -m venv .venv
    source .venv/bin/activate

    # Windows
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Set Up Environment Variables:**
    * Create a file named `.env` in the project root directory.
    * Add your OpenAI API key to it:
        ```env
        OPENAI_API_KEY=your_openai_api_key_here
        ```
    * **Important:** Ensure `.env` is listed in your `.gitignore` file to avoid accidentally committing your API key.

6.  **Run the FastAPI Server:**
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
    ```
    * `main:app`: Tells uvicorn to find the `app` object inside the `main.py` file.
    * `--reload`: Automatically restarts the server when code changes are detected (useful for development).
    * `--host 0.0.0.0`: Makes the server accessible from other devices on your network (use `127.0.0.1` for local access only).
    * `--port 8000`: Specifies the port to run on.

7.  **Access the API:**
    * The API will be running at `http://127.0.0.1:8000` (or `http://0.0.0.0:8000`).
    * You can access the auto-generated API documentation (Swagger UI) at `http://127.0.0.1:8000/docs`.

## Testing the API

1.  **Ensure the server is running** (see step 6 above).
2.  **Run the test script:**
    ```bash
    python testapi.py
    ```
    This script will:
    * Use the files specified within it (e.g., `testcases/transformers.bib` and `testcases/citations.json`).
    * Send a POST request to `http://127.0.0.1:8000/format/`.
    * Print the HTTP status code and the JSON response received from the API.

3.  **Manual Testing:**
    * Use tools like `curl`, Postman, or the Swagger UI (`/docs`) to send requests to the `/format/` endpoint, uploading your own input files and schema files.

Sources and related content
