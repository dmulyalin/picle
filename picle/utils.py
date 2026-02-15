import traceback

from typing import Any, Callable
from pydantic_core import PydanticOmit, core_schema
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue


def run_print_exception(func: Callable) -> Callable:
    """Decorator that wraps a function and prints the traceback if an exception occurs."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            tb = traceback.format_exc()
            print(f"Function {str(func)} execution error:\n{tb}")

    return wrapper


def generate_json_schema(model: Any) -> dict:
    """Generate a JSON schema for the given Pydantic model.

    Uses a custom schema generator that omits fields whose types are
    not valid for JSON schema (e.g. callables).

    :param model: Pydantic model class to generate the schema for.
    :return: dictionary representing the JSON schema.
    """

    class MyGenerateJsonSchema(GenerateJsonSchema):

        def handle_invalid_for_json_schema(
            self, schema: core_schema.CoreSchema, error_info: str
        ) -> JsonSchemaValue:
            raise PydanticOmit

    return model.model_json_schema(
        schema_generator=MyGenerateJsonSchema,
    )
