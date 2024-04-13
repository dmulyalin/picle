import json
import pprint

from typing import List, Union, Optional, Callable, Any
from pydantic import ValidationError, BaseModel, StrictStr, Field, StrictBool, StrictInt

try:
    from yaml import dump as yaml_dump

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from rich.console import Console as rich_console
    from rich.table import Table as rich_table
    from rich.pretty import pprint as rich_pprint

    RICHCONSOLE = rich_console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class Filters(BaseModel):
    include: Any = Field(
        None,
        description="Filter output by pattern inclusion",
        json_schema_extra={"function": "filter_include"},
    )
    exclude: Any = Field(
        None,
        description="Filter output by pattern exclusion",
        json_schema_extra={"function": "filter_exclude"},
    )

    @staticmethod
    def filter_include(data: Any, include: Any = None) -> str:
        """
        Filter data line by line using provided pattern. Returns
        only lines that contains requested ``include`` pattern.

        :param data: data to filter
        :param include: pattern to filter data
        """
        include = str(include)
        return "\n".join([line for line in str(data).splitlines() if include in line])

    @staticmethod
    def filter_exclude(data: Any, exclude: Any = None) -> str:
        """
        Filter data line by line using provided pattern. Returns
        only lines that does not contains requested ``exclude`` pattern.

        :param data: data to filter
        :param exclude: pattern to filter data
        """
        exclude = str(exclude)
        return "\n".join(
            [line for line in str(data).splitlines() if exclude not in line]
        )


class Formatters(BaseModel):
    pprint: Any = Field(
        None,
        description="Convert results to PPRINT string",
        json_schema_extra={"function": "formatter_pprint"},
    )
    json_: Union[dict, list] = Field(
        None,
        description="Convert results to JSON string",
        json_schema_extra={"function": "formatter_json"},
        alias="json",
    )
    yaml: Union[dict, list] = Field(
        None,
        description="Convert results to YAML string",
        json_schema_extra={"function": "formatter_yaml"},
    )
    kv: dict = Field(
        None,
        description="Convert results to Key-Value string",
        json_schema_extra={"function": "formatter_kv"},
    )

    @staticmethod
    def formatter_pprint(data: Any) -> str:
        """
        Function to pretty print results using python ``pprint`` module

        :param data: any data to pretty print
        """
        return pprint.pformat(data, indent=4)

    @staticmethod
    def formatter_json(data: Any) -> str:
        """
        Function to transform results into JSON string

        :param data: any data to convert
        """
        return json.dumps(data, indent=4, sort_keys=True)

    @staticmethod
    def formatter_yaml(data: Any) -> str:
        """
        Function to transform results into YAML string

        :param data: any data to convert
        """
        if HAS_YAML:
            return yaml_dump(data, default_flow_style=False)
        else:
            return data

    @staticmethod
    def formatter_kv(data: dict) -> str:
        """
        Function to format dictionary result as a key: value output

        :param data: dictionary to format
        """
        return "\n".join([f" {k}: {v}" for k, v in data.items()])


class Outputters(BaseModel):
    rich_json: Union[dict, list] = Field(
        None,
        description="Pretty print JSON string using Rich",
        json_schema_extra={"function": "outputter_rich_json"},
    )
    rich_print: Any = Field(
        None,
        description="Pretty print output using Rich",
        json_schema_extra={"function": "outputter_rich_print"},
    )

    @staticmethod
    def outputter_rich_json(data: Union[dict, list]) -> None:
        """
        Function to pretty print JSON string using Rich library

        :param data: any data to print
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        if not isinstance(data, str):
            data = json.dumps(data)

        # data should be a json string
        try:
            if HAS_RICH:
                RICHCONSOLE.print_json(data, sort_keys=True, indent=4)
            else:
                print(data)
        except Exception as e:
            print(f"ERROR: Data is not a valid JSON string: '{data}', error: '{e}'")

    @staticmethod
    def outputter_rich_print(data: Any) -> None:
        """
        Function to pretty print output using Rich library

        :param data: any data to print
        """
        if HAS_RICH:
            RICHCONSOLE.print(data)
        else:
            print(data)


class PipeFunctionsModel(Filters, Formatters, Outputters):
    """
    Collection of common pipe functions to use in PICLE shell models
    """

    class PicleConfig:
        pipe = "self"
