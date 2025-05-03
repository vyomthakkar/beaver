import json
import tiktoken
import copy
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---

# Cache for resolved definitions during token counting to avoid redundant work
resolve_cache_for_counting = {}

def resolve_refs_for_counting(schema_part, full_schema):
    """
    Recursively resolves $ref pointers for accurate token counting.
    Uses a simple cache (`resolve_cache_for_counting`) shared across calls
    for a single property's count calculation.
    NOTE: Simplified resolver. Consider `jsonref` for production.
    """
    if isinstance(schema_part, dict):
        if '$ref' in schema_part:
            ref_path = schema_part['$ref']
            # Use cache if available
            if ref_path in resolve_cache_for_counting:
                return copy.deepcopy(resolve_cache_for_counting[ref_path])

            if ref_path.startswith('#/definitions/'):
                def_name = ref_path.split('/')[-1]
                definition = full_schema.get('definitions', {}).get(def_name)
                if definition:
                    # Store placeholder for cycle detection (very basic)
                    resolve_cache_for_counting[ref_path] = {"$ref_processing": ref_path}
                    resolved = resolve_refs_for_counting(definition, full_schema)
                    # Cache the fully resolved result
                    resolve_cache_for_counting[ref_path] = resolved
                    return copy.deepcopy(resolved) # Return a copy
                else:
                    logging.warning(f"Reference not found during resolution: {ref_path}")
                    return schema_part # Return original ref dict
            else:
                 logging.warning(f"Unsupported reference type encountered: {ref_path}")
                 return schema_part # Return original ref dict
        else:
            resolved_dict = {}
            for key, value in schema_part.items():
                resolved_dict[key] = resolve_refs_for_counting(value, full_schema)
            return resolved_dict
    elif isinstance(schema_part, list):
        return [resolve_refs_for_counting(item, full_schema) for item in schema_part]
    else:
        return schema_part

def get_token_count(schema_part, tokenizer):
    """ Estimates token count for a schema part using JSON serialization. """
    try:
        # Use compact JSON separators for potentially smaller token count
        schema_string = json.dumps(schema_part, separators=(',', ':'))
        return len(tokenizer.encode(schema_string))
    except TypeError as e:
        logging.error(f"Serialization error during token counting: {e} for part {str(schema_part)[:100]}...")
        return 0 # Or handle differently

# Cache for dependency lookups to avoid re-calculating for the same definition
dependency_cache = {}

def get_direct_dependencies(schema_part, full_schema):
    """ Finds only the definition names directly referenced ($ref) by this part. """
    deps = set()
    if isinstance(schema_part, dict):
        if '$ref' in schema_part:
            ref_path = schema_part['$ref']
            if ref_path.startswith('#/definitions/'):
                deps.add(ref_path.split('/')[-1])
            # NOTE: Does not recurse into the *resolved* definition here,
            # only finds refs in the current structure.
        else:
            for value in schema_part.values():
                deps.update(get_direct_dependencies(value, full_schema))
    elif isinstance(schema_part, list):
        for item in schema_part:
            deps.update(get_direct_dependencies(item, full_schema))
    return deps

def get_all_dependencies(start_def_names, full_schema):
    """
    Finds all definition names required by a starting set, including nested dependencies.
    Uses the global `dependency_cache`.
    """
    all_req_defs = set(start_def_names)
    queue = list(start_def_names) # Definitions whose dependencies we need to check

    while queue:
        def_name = queue.pop(0)

        if def_name in dependency_cache:
            direct_deps = dependency_cache[def_name]
        else:
            definition_body = full_schema.get('definitions', {}).get(def_name)
            if definition_body:
                direct_deps = get_direct_dependencies(definition_body, full_schema)
                dependency_cache[def_name] = direct_deps # Cache the result
            else:
                direct_deps = set()
                logging.warning(f"Definition '{def_name}' not found while finding dependencies.")

        # Add new dependencies to the required set and the queue to check their dependencies
        for dep in direct_deps:
            if dep not in all_req_defs:
                all_req_defs.add(dep)
                queue.append(dep) # Need to check dependencies of this newly added def

    return all_req_defs


# --- Main Chunking Function ---

def create_schema_chunks(schema, tokenizer_name="cl100k_base", threshold=10000, sort_props=True):
    """
    Creates schema chunks based on top-level properties, batched by token count.
    Each chunk includes the properties and all necessary definitions.

    Args:
        schema (dict): The loaded JSON schema.
        tokenizer_name (str): Name of the tiktoken tokenizer.
        threshold (int): Max token count per batch (for properties).
        sort_props (bool): Sort properties alphabetically before batching.

    Returns:
        list[dict]: A list of minimal schema chunks (as Python dicts).
                    Returns empty list if input schema is invalid.
    """
    global resolve_cache_for_counting, dependency_cache
    resolve_cache_for_counting.clear() # Clear cache for each run
    dependency_cache.clear()           # Clear cache for each run


    if 'properties' not in schema or not isinstance(schema.get('properties'), dict):
        logging.error("Schema is missing a valid top-level 'properties' object.")
        return []
    if not isinstance(schema.get('definitions'), dict):
        logging.warning("Schema is missing a 'definitions' object. Refs may not resolve.")
        schema['definitions'] = {} # Ensure it exists for lookups

    try:
        tokenizer = tiktoken.get_encoding(tokenizer_name)
    except Exception as e:
        logging.error(f"Failed to initialize tokenizer '{tokenizer_name}': {e}")
        return []

    top_level_props_defs = schema['properties']
    prop_token_counts = {}
    prop_direct_dependencies = {} # Store direct dependencies found for each prop

    logging.info("Step 1: Calculating token counts and direct dependencies for top-level properties...")
    # 1. Calculate resolved token count and find direct dependencies for each prop
    for prop_name, prop_definition in top_level_props_defs.items():
        # --- Token Count ---
        resolve_cache_for_counting.clear() # Use fresh cache for each property's count resolution
        resolved_definition = resolve_refs_for_counting(prop_definition, schema)
        token_count = get_token_count(resolved_definition, tokenizer)
        prop_token_counts[prop_name] = token_count
        logging.debug(f"  - Property '{prop_name}': {token_count} tokens (resolved).")
        if token_count > threshold:
             logging.warning(f"    Property '{prop_name}' ({token_count} tokens) "
                             f"alone exceeds threshold ({threshold}).")

        # --- Direct Dependencies ---
        direct_deps = get_direct_dependencies(prop_definition, schema)
        prop_direct_dependencies[prop_name] = direct_deps
        logging.debug(f"  - Property '{prop_name}': Direct dependencies {direct_deps}")

    logging.info("Step 2: Batching properties based on token counts...")
    # 2. Batch properties based on token counts
    property_batches = []
    current_batch = []
    current_batch_tokens = 0

    property_names = list(top_level_props_defs.keys())
    if sort_props:
        property_names.sort()

    for prop_name in property_names:
        token_count = prop_token_counts[prop_name]

        # Decide if current prop starts a new batch
        if current_batch and (current_batch_tokens + token_count > threshold):
             property_batches.append(current_batch)
             logging.debug(f"  Finalized Batch (Props): {current_batch} ({current_batch_tokens} tokens)")
             current_batch = [prop_name]
             current_batch_tokens = token_count
        else:
             # Add to current batch
             current_batch.append(prop_name)
             current_batch_tokens += token_count

    # Add the last batch
    if current_batch:
        property_batches.append(current_batch)
        logging.debug(f"  Finalized Batch (Props): {current_batch} ({current_batch_tokens} tokens)")

    logging.info(f"Created {len(property_batches)} property batches.")
    logging.info("Step 3: Generating minimal schema chunks for each batch...")
    
    # --- Step 2.5: Validation - Check Required Field Coverage ---
    logging.info("Step 2.5: Validating coverage of required fields...")
    validation_passed = True # Assume pass initially
    original_required = schema.get('required', [])
    if not isinstance(original_required, list):
        logging.warning("Original schema 'required' field is not a list. Skipping validation.")
        original_required = []

    if original_required:
        all_chunked_properties = set()
        for batch in property_batches:
            all_chunked_properties.update(batch)

        missing_required = set(original_required) - all_chunked_properties
        
        print(f"{missing_required=}")
        print(f"{all_chunked_properties=}")
        print(f"{set(schema['properties'].keys())=}")
        print(f"{len(set(schema['properties'].keys()))=}")
        print(f"{len(all_chunked_properties)=}")
        
        if not missing_required:
            logging.info("Validation successful: All original required fields are covered by the generated batches.")
        else:
            logging.error(f"Validation FAILED: The following required fields from the original schema "
                          f"are NOT covered by any generated batch: {missing_required}")
            validation_passed = False
            # Decide if you want to stop processing here or just log
            # For now, we log the error and continue, but you might want to return None or raise an Exception
            # return None # Example of stopping execution
    else:
        logging.info("No top-level required fields found in the original schema to validate coverage.")
    # ---------------------------------------------------------
    
    # 3. Generate minimal schema for each batch
    schema_chunks = []
    for i, batch_props in enumerate(property_batches):
        logging.debug(f"  Generating chunk for batch {i+1}: {batch_props}")
        # Collect properties for this chunk
        properties_for_chunk = {
            p_name: top_level_props_defs[p_name] for p_name in batch_props
        }

        # Find all required definitions (direct + nested)
        start_deps = set()
        for p_name in batch_props:
            start_deps.update(prop_direct_dependencies.get(p_name, set()))

        logging.debug(f"    Initial direct dependencies for batch: {start_deps}")
        all_required_def_names = get_all_dependencies(start_deps, schema)
        logging.debug(f"    All required definitions (incl. nested): {all_required_def_names}")

        # Collect the actual definition bodies
        definitions_for_chunk = {
            def_name: schema['definitions'][def_name]
            for def_name in all_required_def_names
            if def_name in schema['definitions'] # Ensure definition exists
        }

        # --- Optional: Filter 'required' list for the chunk ---
        original_required = schema.get('required', [])
        required_for_chunk = [req for req in original_required if req in batch_props]
        # ----------------------------------------------------

        # Construct the minimal schema chunk
        chunk_schema = {
            # Include $schema to help LLM understand the syntax
            "$schema": schema.get("$schema", "http://json-schema.org/draft-07/schema#"),
            "type": "object",
            "properties": properties_for_chunk,
        }
        # Only add definitions block if needed
        if definitions_for_chunk:
            chunk_schema["definitions"] = definitions_for_chunk
        # Only add required block if needed for this chunk's props
        if required_for_chunk:
             chunk_schema["required"] = required_for_chunk
        # Optionally add description/title if helpful?
        # chunk_schema["description"] = f"Schema chunk for properties: {', '.join(batch_props)}"

        schema_chunks.append(chunk_schema)
        logging.debug(f"    Generated chunk schema with {len(properties_for_chunk)} properties and {len(definitions_for_chunk)} definitions.")

    logging.info(f"Schema chunk generation complete. Produced {len(schema_chunks)} chunks.")
    return schema_chunks

# --- Example Usage ---

# Load your schema
try:
    # Assuming your schema is in a file named 'schema.json'
    # with open('testcases/citations.json', 'r') as f:
    # with open('testcases/ga.json', 'r') as f:
    with open('testcases/resume.json', 'r') as f:
        cff_schema = json.load(f)
    logging.info("Successfully loaded schema from schema.json")
except FileNotFoundError:
    logging.error("schema.json not found. Please provide the correct path.")
    exit()
except json.JSONDecodeError as e:
     logging.error(f"Could not decode JSON from schema file: {e}")
     exit()

# --- Parameters ---
TOKENIZER = "cl100k_base"  # For GPT-3.5/4
# TOKENIZER = "..." # Use appropriate tokenizer if using Gemini or other models
TOKEN_THRESHOLD = 10000   # Max combined *resolved* token size for properties in a batch
SORT_PROPS = True         # Sort props alphabetically for consistent batches

# --- Run Chunking ---
generated_chunks = create_schema_chunks(
    cff_schema,
    tokenizer_name=TOKENIZER,
    threshold=TOKEN_THRESHOLD,
    sort_props=SORT_PROPS
)

# --- Output Results (Optional) ---
if generated_chunks:
    print(f"\n--- Generated {len(generated_chunks)} Schema Chunks ---")
    for i, chunk in enumerate(generated_chunks):
        chunk_props = list(chunk.get('properties', {}).keys())
        num_defs = len(chunk.get('definitions', {}))
        # Optional: Estimate token count of the final generated chunk itself
        try:
             chunk_tokenizer = tiktoken.get_encoding(TOKENIZER)
             chunk_token_count = get_token_count(chunk, chunk_tokenizer)
             print(f"Chunk {i+1} (Properties: {chunk_props}) "
                   f"({num_defs} definitions) "
                   f"(Est. Chunk Tokens: {chunk_token_count})")
        except Exception as e:
             print(f"Chunk {i+1} (Properties: {chunk_props}) ({num_defs} definitions) - Error estimating chunk tokens: {e}")

        # Optional: Save each chunk to a file
        with open(f'schema_chunk_{i+1}.json', 'w') as f:
            json.dump(chunk, f, indent=2)
else:
    print("No schema chunks were generated.")