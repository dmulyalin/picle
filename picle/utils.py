import traceback

from pydantic_core import PydanticOmit, core_schema
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue


def run_print_exception(func):
    """Decorator to run function and print exception if error occurred"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            tb = traceback.format_exc()
            print(f"Function {str(func)} execution error:\n{tb}")

    return wrapper


def generate_json_schema(model):
    """Print manual"""

    class MyGenerateJsonSchema(GenerateJsonSchema):
        # def callable_schema(self, schema):
        #     print(schema)
        #     raise SystemExit

        def handle_invalid_for_json_schema(
            self, schema: core_schema.CoreSchema, error_info: str
        ) -> JsonSchemaValue:
            raise PydanticOmit

    return model.model_json_schema(
        schema_generator=MyGenerateJsonSchema,
    )
