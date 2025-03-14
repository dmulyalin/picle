import json
import pprint

from typing import List, Union, Optional, Callable, Any
from pydantic import ValidationError, BaseModel, StrictStr, Field, StrictBool, StrictInt
from pydantic._internal._model_construction import ModelMetaclass
from collections.abc import Mapping
from numbers import Number

try:
    from yaml import dump as yaml_dump

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from rich.console import Console as rich_console
    from rich.table import Table as RICHTABLE
    from rich.tree import Tree as RICHTREE
    from rich.markdown import Markdown

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
    rich_table: Any = Field(
        None,
        description="Pretty print table output using Rich",
        json_schema_extra={"function": "outputter_rich_table"},
    )
    rich_yaml: Any = Field(
        None,
        description="Pretty print YAML output using Rich",
        json_schema_extra={"function": "outputter_rich_yaml"},
    )
    rich_markdown: Any = Field(
        None,
        description="Print markdown text to terminal",
        json_schema_extra={"function": "outputter_rich_markdown"},
    )
    nested: Any = Field(
        None,
        description="Print data in nested format",
        json_schema_extra={"function": "outputter_nested"},
    )

    @staticmethod
    def outputter_nested(data: Union[dict, list], initial_indent: int = 0) -> None:
        """
        Recursively formats and prints nested data structures (dictionaries and lists)
        in a human-readable format.

        :param data: nested data structure to be formatted and printed.
        :param initial_indent: initial indentation level.
        """

        def ustring(indent, msg, prefix="", suffix=""):
            indent *= " "
            fmt = "{0}{1}{2}{3}"
            return fmt.format(indent, prefix, msg, suffix)

        def nest(ret, indent, prefix, out):
            if isinstance(ret, bytes):
                try:
                    ret = ret.decode("utf-8")
                except UnicodeDecodeError:
                    ret = str(ret)

            if ret is None or ret is True or ret is False:
                out.append(ustring(indent, ret, prefix=prefix))
            elif isinstance(ret, Number):
                out.append(ustring(indent, repr(ret), prefix=prefix))
            elif isinstance(ret, str):
                first_line = True
                for line in ret.splitlines():
                    line_prefix = " " * len(prefix) if not first_line else prefix
                    out.append(ustring(indent, line, prefix=line_prefix))
                    first_line = False
            elif isinstance(ret, (list, tuple)):
                for ind in ret:
                    if isinstance(ind, (list, tuple, Mapping)):
                        out.append(ustring(indent, "|_"))
                        prefix = "" if isinstance(ind, Mapping) else "- "
                        nest(ind, indent + 2, prefix, out)
                    else:
                        nest(ind, indent, "- ", out)
            elif isinstance(ret, Mapping):
                if indent:
                    out.append(ustring(indent, "----------"))

                for key in ret.keys():
                    val = ret[key]
                    out.append(ustring(indent, key, suffix=":", prefix=prefix))
                    nest(val, indent + 4, "", out)
            return out

        lines = nest(data, initial_indent, "", [])
        lines = "\n".join(lines)

        if HAS_RICH:
            RICHCONSOLE.print(lines)
        else:
            print(lines)

    @staticmethod
    def outputter_rich_yaml(data: Union[dict, list], initial_indent: int = 0) -> None:
        """
        Function to pretty print YAML string using Rich library

        :param data: any data to print
        :param initial_indent: initial indentation level.
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        # data should be a YAML string
        try:
            if HAS_RICH and HAS_YAML:
                data = yaml_dump(data, default_flow_style=False, sort_keys=False)
                # add  indent
                data = "\n".join(
                    [f"{' ' * initial_indent}{i}" for i in data.splitlines()]
                )
                RICHCONSOLE.print(data)
            else:
                print(data)
        except Exception as e:
            print(f"ERROR: Data is not a valid YAML string:\n{data}\n\nError: '{e}'")

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
            print(f"ERROR: Data is not a valid JSON string:\n{data}\n\nError: '{e}'")

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

    @staticmethod
    def outputter_rich_table(
        data: list[dict], headers: list = None, title: str = None, sortby: str = None
    ):
        """
        Function to pretty print output in table format using Rich library

        :param data: list of dictionaries to print
        """
        if not HAS_RICH or not isinstance(data, list):
            print(data)
            return

        headers = headers or list(data[0].keys())
        table = RICHTABLE(title=title, box=False)

        # add table columns
        for h in headers:
            table.add_column(h, justify="left", no_wrap=True)

        # sort the table
        if sortby:
            sorted_data = sorted(data, key=lambda d: d[sortby])
        else:
            sorted_data = data

        # add table rows
        for item in sorted_data:
            cells = [item.get(h, "") for h in headers]
            table.add_row(*cells)

        RICHCONSOLE.print(table)

    @staticmethod
    def outputter_rich_markdown(data: Any) -> None:
        """
        Function to print markdown output using Rich library

        :param data: any data to print
        """
        if not isinstance(data, str):
            data = str(data)

        if HAS_RICH:
            RICHCONSOLE.print(Markdown(data))
        else:
            print(data)


class PipeFunctionsModel(Filters, Formatters, Outputters):
    """
    Collection of common pipe functions to use in PICLE shell models
    """

    class PicleConfig:
        pipe = "self"


class MAN(BaseModel):
    """
    Model with manual/documentation related functions
    """

    tree: Optional[StrictStr] = Field(
        None,
        description="Print commands tree for shell model specified by dot separated path e.g. model.shell.command",
        json_schema_extra={"function": "print_model_tree", "root_model": True},
    )

    @staticmethod
    def _construct_model_tree(model, tree: RICHTREE, path: list) -> RICHTREE:
        for field_name, field in model.model_fields.items():
            if (
                path
                and field_name != path[0]
                and field.alias != path[0]
                and field.serialization_alias != path[0]
            ):
                continue
            # form tree element label
            label = [
                f"[bold]{'*' if field.is_required() else ''}"
                f"{field.alias or field.serialization_alias or field_name}:[/bold]    {field.description}"
            ]
            if field.get_default() is not None and field.annotation != Callable:
                default_value = field.get_default()
                if isinstance(
                    default_value, (str, int, float, bool, list, dict, tuple, set)
                ):
                    label.append(f"default '{field.get_default()}'")
            if field.examples:
                examples = (
                    field.examples
                    if isinstance(field.examples, list)
                    else [field.examples]
                )
                label.append(f"examples: {', '.join(examples)}")
            next_tree = tree.add(", ".join(label))
            # recurse to next level model
            if isinstance(field.annotation, ModelMetaclass):
                MAN._construct_model_tree(field.annotation, next_tree, path[1:])

        return tree

    @staticmethod
    def print_model_tree(root_model, **kwargs) -> None:
        """
        Method to print model tree for shell model specified by dot separated path e.g. model.shell.command

        :param root_model: PICLE App root model to print tree for
        """
        path = kwargs["tree"].split(".") if kwargs.get("tree") else []
        rich_tree = RICHTREE("[bold]root[/bold]")
        RICHCONSOLE.print(
            MAN._construct_model_tree(
                model=root_model.model_construct(), tree=rich_tree, path=path
            )
        )
