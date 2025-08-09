import json
import pprint
import logging
import os
import copy

from enum import Enum
from typing import List, Union, Optional, Callable, Any
from pydantic import ValidationError, BaseModel, StrictStr, Field, StrictBool, StrictInt
from pydantic_core import PydanticOmit, core_schema
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic._internal._model_construction import ModelMetaclass
from collections.abc import Mapping
from numbers import Number

log = logging.getLogger(__name__)

try:
    from yaml import dump as yaml_dump

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import tabulate as tabulate_lib

    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

try:
    from rich.console import Console as rich_console
    from rich.table import Table as RICHTABLE
    from rich.tree import Tree as RICHTREE
    from rich.markdown import Markdown

    RICHCONSOLE = rich_console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# --------------------------------------------------------------------------------
# FILTERS
# --------------------------------------------------------------------------------


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


# --------------------------------------------------------------------------------
# OUTPUTTERS
# --------------------------------------------------------------------------------


class TabulateTableFmt(str, Enum):
    plain = "plain"
    simple = "simple"
    github = "github"
    grid = "grid"
    simple_grid = "simple_grid"
    rounded_grid = "rounded_grid"
    heavy_grid = "heavy_grid"
    mixed_grid = "mixed_grid"
    double_grid = "double_grid"
    fancy_grid = "fancy_grid"
    outline = "outline"
    simple_outline = "simple_outline"
    rounded_outline = "rounded_outline"
    heavy_outline = "heavy_outline"
    mixed_outline = "mixed_outline"
    double_outline = "double_outline"
    fancy_outline = "fancy_outline"
    pipe = "pipe"
    orgtbl = "orgtbl"
    asciidoc = "asciidoc"
    jira = "jira"
    presto = "presto"
    pretty = "pretty"
    psql = "psql"
    rst = "rst"
    mediawiki = "mediawiki"
    moinmoin = "moinmoin"
    youtrack = "youtrack"
    html = "html"
    unsafehtml = "unsafehtml"
    latex = "latex"
    latex_raw = "latex_raw"
    latex_booktabs = "latex_booktabs"
    latex_longtable = "latex_longtable"
    textile = "textile"
    tsv = "tsv"


class TabulateTableOutputter(BaseModel):
    tablefmt: TabulateTableFmt = Field(None, description="Table format")
    headers: Union[StrictStr, List[str]] = Field(None, description="Table headers")
    sortby: StrictStr = Field(None, description="Column name to sort by")
    reverse: StrictBool = Field(
        None,
        description="Reverse table order when doing sortby",
        json_schema_extra={"presence": True},
    )
    headers_exclude: Union[StrictStr, List[str]] = Field(
        None, description="List of headers to exclude", alias="headers-exclude"
    )
    showindex: StrictBool = Field(
        None,
        description="Show table rows indexes",
        json_schema_extra={"presence": True},
    )
    maxcolwidths: StrictInt = Field(
        None, description="Maximum width of the column before wrapping text"
    )

    class PicleConfig:
        pipe = "picle.models.PipeFunctionsModel"

    @staticmethod
    def run(*args, **kwargs):
        return Outputters.outputter_tabulate_table(*args, **kwargs)


class RichTableOutputter(BaseModel):
    title: Optional[StrictStr] = Field(None, description="Table title")
    headers: List[str] = Field(None, description="Table headers")
    sortby: Optional[StrictStr] = Field(None, description="Column name to sort by")

    @staticmethod
    def run(*args, **kwargs):
        return Outputters.outputter_rich_table(*args, **kwargs)


class Outputters(BaseModel):
    pprint: Any = Field(
        None,
        description="Convert results to pretty string",
        json_schema_extra={"function": "outputter_pprint"},
    )
    json_: Union[dict, list] = Field(
        None,
        description="Print JSON string using Rich",
        json_schema_extra={"function": "outputter_json"},
        alias="json",
    )
    yaml: Any = Field(
        None,
        description="Print YAML output using Rich",
        json_schema_extra={"function": "outputter_yaml"},
    )
    markdown: Any = Field(
        None,
        description="Print markdown text to terminal",
        json_schema_extra={"function": "outputter_rich_markdown"},
        alias="markdown",
    )
    nested: Any = Field(
        None,
        description="Print data in nested format",
        json_schema_extra={"function": "outputter_nested"},
    )
    save: StrictStr = Field(
        None,
        description="Save results to a file",
        json_schema_extra={"function": "outputter_save"},
    )
    table: TabulateTableOutputter = Field(
        None,
        description="Format results as a table",
        json_schema_extra={"function": "outputter_tabulate_table"},
    )
    rich_table: RichTableOutputter = Field(
        None,
        description="Print table output using Rich",
        json_schema_extra={"function": "outputter_rich_table"},
        alias="rich-table",
    )
    kv: dict = Field(
        None,
        description="Convert dictionary result to Key-Value string",
        json_schema_extra={"function": "outputter_kv"},
    )

    @staticmethod
    def outputter_kv(data: dict) -> str:
        """
        Function to format dictionary result as a key: value output

        :param data: dictionary to format
        """
        return "\n".join([f" {k}: {v}" for k, v in data.items()])

    @staticmethod
    def outputter_pprint(data: Any) -> str:
        """
        Function to pretty print results using python ``pprint`` module

        :param data: any data to pretty print
        """
        return pprint.pformat(data, indent=4)

    @staticmethod
    def outputter_nested(
        data: Union[dict, list],
        initial_indent: int = 0,
        with_tables: bool = False,
        tabulate_kwargs: dict = None,
    ) -> None:
        """
        Recursively formats and prints nested data structures (dictionaries and lists)
        in a human-readable format.

        :param data: nested data structure to be formatted and printed.
        :param initial_indent: initial indentation level.
        :param with_tables: if True, will format flat lists as Tabulate tables.
        """
        tabulate_kwargs = tabulate_kwargs or {"tablefmt": "simple"}

        def is_dictionary_list(data):
            for item in data:
                if not isinstance(item, Mapping):
                    return False
                for i in item.values():
                    if isinstance(i, (list, tuple, Mapping)):
                        return False
            return True

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
                # make a text table if it is a flat list
                if with_tables and is_dictionary_list(ret):
                    table = Outputters.outputter_tabulate_table(ret, **tabulate_kwargs)
                    nest(table, indent + 2, prefix, out)
                else:
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

        # make sure data is sorted
        try:
            if isinstance(data, dict):
                data = dict(sorted(data.items()))
            elif isinstance(data, list):
                data = list(sorted(data))
        except Exception as e:
            log.warning(f"Nested outputter data sorting failed: '{e}'")

        lines = nest(data, initial_indent, "", [])
        lines = "\n".join(lines)

        return lines

    @staticmethod
    def outputter_rich_table(
        data: list[dict], headers: list = None, title: str = None, sortby: str = None
    ):
        original_data = copy.deepcopy(data)

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

        return table

    @staticmethod
    def outputter_yaml(
        data: Union[dict, list], absolute_indent: int = 0, indent: int = 2
    ) -> None:
        """
        Function to pretty print YAML string using Rich library

        :param data: any data to print
        :param absolute_indent: indentation to prepend for entire output
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        # data should be a YAML string
        try:
            if HAS_YAML:
                data = yaml_dump(
                    data, default_flow_style=False, sort_keys=True, indent=indent
                )
                # add  indent
                if absolute_indent:
                    data = "\n".join(
                        [f"{' ' * absolute_indent}{i}" for i in data.splitlines()]
                    )
        except Exception as e:
            print(f"ERROR: Data is not a valid YAML string:\n{data}\n\nError: '{e}'")

        return data

    @staticmethod
    def outputter_json(data: Union[dict, list], indent: int = 4) -> None:
        """
        Function to pretty print JSON string using Rich library

        :param data: any data to print
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        # data should be a json string
        try:
            data = json.dumps(data, indent=indent, sort_keys=True)
        except Exception as e:
            print(f"ERROR: Data is not a valid JSON string:\n{data}\n\nError: '{e}'")

        return data

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

        # signal to Picle that data was printed by sending None
        # as second argument, which will be used as a default outputter
        return data, None

    @staticmethod
    def outputter_save(data: Any, save: str) -> None:
        """
        Function to output data into a file

        :param data: any data to print
        """
        # create directories
        abspath = os.path.abspath(save)
        dirs = os.path.split(abspath)[0]
        os.makedirs(dirs, exist_ok=True)

        # save data to file
        with open(save, "w") as f:
            if isinstance(data, str):
                f.write(data)
            else:
                f.write(str(data))

        return data

    @staticmethod
    def outputter_tabulate_table(
        data: list,
        headers_exclude: list = None,
        sortby: str = None,
        reverse: bool = False,
        tablefmt: str = "grid",
        headers: list = None,
        showindex: bool = True,
        maxcolwidths: int = None,
    ) -> None:
        """
        Formats and outputs data as a text table.

        This function uses the `tabulate` library to format a list of dictionaries or
        lists of lists of dictionaries into a table with various styles and options
        for customization.

        Parameters:

            data (list): A list of dictionaries or list of lists to be formatted into a table.
                If it is list of lists, the function merges nested lists.
            headers (list or str, optional): Specifies the table headers. Can be:

                - A list of headers.
                - A comma-separated string of headers.
                - "keys" to use dictionary keys as headers.

            showindex (bool, optional): If True, includes an index column in the table.
            headers_exclude (list, optional): A list or comma-separated string of headers to exclude from the table.
            sortby (str, optional): The key name to sort the table by. If None, no sorting is applied.
            reverse (bool, optional): If True, reverses the sort order. Defaults to False.
        """
        if not HAS_TABULATE:
            log.error(
                "PICLE Table outputter tabulate library import failed, install: pip install tabulate"
            )
            return data
        if not isinstance(data, list):
            log.error("PICLE Table outputter data is not a list")
            return data

        # transform headers to exclude argument
        headers_exclude = headers_exclude or []
        if isinstance(headers_exclude, str) and "," in headers_exclude:
            headers_exclude = [i.strip() for i in headers_exclude.split(",")]

        # form base tabulate arguments
        if isinstance(headers, str):
            headers = [i.strip() for i in headers.split(",")]
        elif headers is None:
            headers = "keys"

        tabulate_kw = {
            "headers": headers,
            "tablefmt": tablefmt,
            "maxcolwidths": maxcolwidths,
        }

        # form singe table out of list of lists
        table_ = []
        while data:
            item = data.pop(0)
            if isinstance(item, list):
                table_.extend(item)
            else:
                table_.append(item)
        data = table_

        # sort results
        if sortby:
            data = sorted(
                data,
                reverse=reverse,
                key=lambda item: str(item.get(sortby, "")),
            )

        # filter table headers if requested to do so
        if headers_exclude:
            data = [
                {k: v for k, v in res.items() if k not in headers_exclude}
                for res in data
            ]

        # transform data content to match headers
        if isinstance(tabulate_kw["headers"], list):
            data = [[item.get(i, "") for i in tabulate_kw["headers"]] for item in data]

        # start index with 1 instead of 0
        if showindex is True:
            showindex = range(1, len(data) + 1)
            tabulate_kw["showindex"] = showindex

        return tabulate_lib.tabulate(data, **tabulate_kw)


class PipeFunctionsModel(Filters, Outputters):
    """
    Collection of common pipe functions to use in PICLE shell models
    """

    class PicleConfig:
        pipe = "self"


# --------------------------------------------------------------------------------
# MAN / DOC
# --------------------------------------------------------------------------------


class MAN(BaseModel):
    """
    Manual and documentation related functions
    """

    tree: Optional[StrictStr] = Field(
        None,
        description="Print commands tree for shell model specified by dot separated path e.g. model.shell.command",
        json_schema_extra={"function": "print_model_tree", "root_model": True},
    )
    json_schema: Optional[StrictStr] = Field(
        None,
        description="Print json schema for shell model specified by dot separated path e.g. model.shell.command",
        json_schema_extra={"function": "print_model_json_schema", "root_model": True},
        alias="json-schema",
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

    @staticmethod
    def _recurse_to_model(model, path: list) -> ModelMetaclass:
        """
        Recurse to model specified by dot separated path e.g. model.shell.command

        :param model: Model to recurse through
        :param path: path to recurse to
        """
        if not path:
            return model

        for field_name, field in model.model_fields.items():
            if (
                field_name == path[0]
                or field.alias == path[0]
                or field.serialization_alias == path[0]
            ):
                # recurse to next level model
                if isinstance(field.annotation, ModelMetaclass):
                    return MAN._recurse_to_model(field.annotation, path[1:])

        return model

    @staticmethod
    def print_model_json_schema(root_model, **kwargs) -> None:
        """
        Method to print model json schema for shell model specified by dot separated path e.g. model.shell.command

        :param root_model: PICLE App root model to print json schema for
        """

        class MyGenerateJsonSchema(GenerateJsonSchema):
            def handle_invalid_for_json_schema(
                self, schema: core_schema.CoreSchema, error_info: str
            ) -> JsonSchemaValue:
                raise PydanticOmit

            def callable_schema(self, schema):
                print(schema)
                raise SystemExit

            def render_warning_message(kind, detail: str) -> None:
                print(kind, detail)

        path = kwargs["json_schema"].split(".") if kwargs.get("json_schema") else []
        model = MAN._recurse_to_model(root_model, path=path)
        return json.dumps(
            model.model_json_schema(schema_generator=MyGenerateJsonSchema),
            indent=4,
            sort_keys=True,
        )
