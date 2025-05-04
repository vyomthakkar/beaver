from schema_conv import extract_document, convert_schema_to_json
from schema_chunk_graph import create_schema_chunks, get_token_count
import tiktoken
import json


def format(input_file, schema):
    schema_json = convert_schema_to_json(schema)
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
        print("-"*100)
        print("schema chunk: ", chunk['properties'].keys())
        print("-"*100)
        chunked_output.append(extract_document(input_file, chunk))
        break
        
    print(chunked_output)
    print(len(chunked_output))


# extract_document('testcases/transformers.bib', convert_schema_to_json('schema_chunk_5.json'))
format('testcases/transformers.bib', 'testcases/citations.json')