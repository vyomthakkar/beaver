# from datamodel_code_generator import InputFileType, DataModelType
# from datamodel_code_generator.parser.jsonschema import JsonSchemaParser
# from datamodel_code_generator.model import get_data_model_types
# from datamodel_code_generator import PythonVersion
# from pathlib import Path

from pathlib import Path
from datamodel_code_generator import InputFileType, generate
from datamodel_code_generator import DataModelType

# schema_text = Path("testcases/citations.json").read_text()
# types = get_data_model_types(
#     DataModelType.PydanticV2BaseModel,
#     target_python_version=PythonVersion.PY_311,
# )
# parser = JsonSchemaParser(
#     schema_text,
#     data_model_type=types.data_model,
#     data_model_root_type=types.root_model,
#     data_model_field_type=types.field_model,
#     data_type_manager_type=types.data_type_manager,
#     dump_resolve_reference_action=types.dump_resolve_reference_action,
# )
# print(parser)
# python_code = parser.parse()
# print("ok")
# print(python_code)

def generate_models(
    schema_path: Path,
    output_path: Path
) -> None:
    """Read a JSON Schema file and emit Pydantic V2 BaseModel classes."""
    schema_text = schema_path.read_text()
    generate(
        schema_text,
        input_file_type=InputFileType.JsonSchema,
        input_filename=str(schema_path),
        output=output_path,
        output_model_type=DataModelType.PydanticV2BaseModel,
        # optional conveniences:
        snake_case_field=True,
        use_schema_description=True,
        allow_population_by_field_name=True,
    )

generate_models(Path("testcases/citations.json"), Path("citations.py"))