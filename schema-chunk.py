import json

input_schema_path = 'testcases/citations.json'

with open(input_schema_path, 'r') as f:
    schema = json.load(f)

# print(schema)

print(len(schema))
print(schema.keys())

# print(schema['definitions'])
# print(schema['definitions']['reference'])

for key, value in schema.items():
    print(f"{key=}")
    print(f"{value=}")
    print("#"*100)

