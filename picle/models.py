from pprint import pformat
from json import dumps as json_dumps
from typing import List, Union, Optional, Callable, Any
from pydantic import ValidationError, BaseModel, StrictStr, Field, StrictBool, StrictInt

try:
    from yaml import dump as yaml_dump

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


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
        description="Pretty print results",
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

    @staticmethod
    def formatter_pprint(data: Any) -> str:
        """
        Function to pretty print results using python ``pprint`` module

        :param data: any data to pretty print
        """
        return pformat(data, indent=4)

    @staticmethod
    def formatter_json(data: Any) -> str:
        """
        Function to transform results into JSON string

        :param data: any data to convert
        """
        return json_dumps(data, indent=4, sort_keys=True)

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


class PipeFunctionsModel(Filters, Formatters):
    """
    Collection of common pipe functions to use in PICLE shell models
    """

    class PicleConfig:
        pipe = "self"
