import json
import pprint
import logging
import os
import shutil
import difflib

from enum import Enum
from typing import List, Union, Optional, Callable, Any
from pathlib import Path
from pydantic import BaseModel, StrictStr, Field, StrictBool, StrictInt
from pydantic_core import PydanticOmit, core_schema
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic._internal._model_construction import ModelMetaclass
from collections.abc import Mapping
from numbers import Number

log = logging.getLogger(__name__)

try:
    import yaml

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
        only lines that contain the requested ``include`` pattern.

        :param data: data to filter
        :param include: pattern to filter data
        """
        include = str(include)
        return "\n".join([line for line in str(data).splitlines() if include in line])

    @staticmethod
    def filter_exclude(data: Any, exclude: Any = None) -> str:
        """
        Filter data line by line using provided pattern. Returns
        only lines that do not contain the requested ``exclude`` pattern.

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
    """Outputter that formats data as a text table using the tabulate library."""

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
    """Outputter that formats data as a Rich table."""

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
        json_schema_extra={"function": "outputter_pprint", "outputter": True},
    )
    json_: Union[dict, list] = Field(
        None,
        description="Print JSON string using Rich",
        json_schema_extra={"function": "outputter_json", "outputter": True},
        alias="json",
    )
    yaml: Any = Field(
        None,
        description="Print YAML output using Rich",
        json_schema_extra={"function": "outputter_yaml", "outputter": True},
    )
    markdown: Any = Field(
        None,
        description="Print markdown text to terminal",
        json_schema_extra={"function": "outputter_rich_markdown", "outputter": True},
        alias="markdown",
    )
    nested: Any = Field(
        None,
        description="Print data in nested format",
        json_schema_extra={"function": "outputter_nested", "outputter": True},
    )
    save: StrictStr = Field(
        None,
        description="Save results to a file",
        json_schema_extra={"function": "outputter_save"},
    )
    table: TabulateTableOutputter = Field(
        None,
        description="Format results as a table",
        json_schema_extra={"function": "outputter_tabulate_table", "outputter": True},
    )
    rich_table: RichTableOutputter = Field(
        None,
        description="Print table output using Rich",
        json_schema_extra={"function": "outputter_rich_table", "outputter": True},
        alias="rich-table",
    )
    kv: dict = Field(
        None,
        description="Convert dictionary result to Key-Value string",
        json_schema_extra={"function": "outputter_kv", "outputter": True},
    )

    @staticmethod
    def outputter_kv(data: dict) -> str:
        """
        Format a dictionary as a key-value output string.

        :param data: dictionary to format.
        :return: formatted key-value string.
        """
        if isinstance(data, str):
            return data
        return "\n".join([f" {k}: {v}" for k, v in data.items()])

    @staticmethod
    def outputter_pprint(data: Any) -> str:
        """
        Pretty-print results using Python's ``pprint`` module.

        :param data: any data to pretty-print.
        :return: nicely formatted string representation.
        """
        if isinstance(data, str):
            return data
        return pprint.pformat(data, indent=4)

    @staticmethod
    def outputter_nested(
        data: Union[dict, list],
        initial_indent: int = 0,
        with_tables: bool = False,
        tabulate_kwargs: dict = None,
    ) -> str:
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
    ) -> Any:
        """
        Format a list of dictionaries as a Rich table.

        :param data: list of dictionaries to display.
        :param headers: column headers; defaults to the keys of the first row.
        :param title: optional table title.
        :param sortby: key name to sort rows by.
        :return: a Rich ``Table`` object, or the original data if Rich is unavailable.
        """
        if not HAS_RICH or not isinstance(data, list):
            return data

        if not data:
            return data

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
            cells = [str(item.get(h, "")) for h in headers]
            table.add_row(*cells)

        return table

    @staticmethod
    def outputter_yaml(
        data: Union[dict, list, bytes], absolute_indent: int = 0, indent: int = 2
    ) -> Any:
        """
        Function to format structured data as YAML string

        :param data: any data to print
        :param absolute_indent: indentation to prepend for entire output
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        if isinstance(data, str):
            return data

        # data should be a YAML string
        try:
            if HAS_YAML:
                data = yaml.safe_dump(
                    data, default_flow_style=False, sort_keys=True, indent=indent
                )
                # add  indent
                if absolute_indent:
                    data = "\n".join(
                        [f"{' ' * absolute_indent}{i}" for i in data.splitlines()]
                    )
            else:
                log.error(
                    "PICLE YAML outputter yaml library import failed, install: pip install pyyaml"
                )
        except Exception as e:
            print(
                f"ERROR: Failed to format data as YAML string:\n{data}\n\nError: '{e}'"
            )

        return data

    @staticmethod
    def outputter_json(data: Union[dict, list, bytes], indent: int = 4) -> Any:
        """
        Function to pretty print JSON string using Rich library

        :param data: any data to print
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        if isinstance(data, str):
            return data

        # data should be a json string
        try:
            data = json.dumps(data, indent=indent, sort_keys=True)
        except Exception as e:
            print(
                f"ERROR: Failed to format data as JSON string:\n{data}\n\nError: '{e}'"
            )

        return data

    @staticmethod
    def outputter_rich_markdown(data: Any) -> Any:
        """
        Function to print markdown output using Rich library

        :param data: any data to print
        """
        if not isinstance(data, str):
            data = str(data)

        if HAS_RICH:
            return Markdown(data)
        else:
            return data

    @staticmethod
    def outputter_save(data: Any, save: str) -> Any:
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
    ) -> Any:
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
        model_cls = model if isinstance(model, type) else type(model)
        for field_name, field in model_cls.model_fields.items():
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
                examples = [str(e) for e in examples]
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
        if HAS_RICH:
            path = kwargs["tree"].split(".") if kwargs.get("tree") else []
            rich_tree = RICHTREE("[bold]root[/bold]")
            RICHCONSOLE.print(
                MAN._construct_model_tree(
                    model=root_model.model_construct(), tree=rich_tree, path=path
                )
            )
        else:
            log.error(
                "PICLE model tree outputter requires Rich library, install: pip install rich"
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

        for field_name, field in (
            model if isinstance(model, type) else type(model)
        ).model_fields.items():
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
    def print_model_json_schema(root_model, **kwargs) -> str:
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
                raise PydanticOmit

            def render_warning_message(kind, detail: str) -> None:
                print(kind, detail)

        path = kwargs["json_schema"].split(".") if kwargs.get("json_schema") else []
        model = MAN._recurse_to_model(root_model, path=path)
        return json.dumps(
            model.model_json_schema(schema_generator=MyGenerateJsonSchema),
            indent=4,
            sort_keys=True,
        )


# --------------------------------------------------------------------------------
# CONFIGURATION MODEL
# --------------------------------------------------------------------------------


class ConfigModelShowCommands(BaseModel):
    configuration: Any = Field(
        None,
        description="Show running configuration content",
        json_schema_extra={"function": "show_config"},
    )
    changes: Any = Field(
        None,
        description="Show uncommitted changes diff between temp and running config",
        json_schema_extra={"function": "show_changes"},
    )

    @staticmethod
    def show_config(shell_command: list) -> dict:
        """
        Load and return the running configuration.

        :param shell_command: The shell command context
        :return: Configuration content dictionary
        """
        model_config = ConfigModel.get_model_config(shell_command)
        config_file = model_config["config_file"]
        return ConfigModel.load_config(config_file)

    @staticmethod
    def show_changes(shell_command: list) -> str:
        """
        Show diff between saved config and uncommitted temp config.

        :param shell_command: The shell command context
        :return: Unified diff string
        """
        model_config = ConfigModel.get_model_config(shell_command)
        config_file = model_config["config_file"]
        temp_file = config_file + ".tmp"

        if not Path(temp_file).exists():
            return "No uncommitted changes"

        saved_content = ConfigModel.load_config(config_file)
        temp_content = ConfigModel.load_config(temp_file)

        saved_lines = yaml.safe_dump(
            saved_content, default_flow_style=False, sort_keys=True, indent=2
        ).splitlines(keepends=True)
        temp_lines = yaml.safe_dump(
            temp_content, default_flow_style=False, sort_keys=True, indent=2
        ).splitlines(keepends=True)

        diff = difflib.unified_diff(
            saved_lines, temp_lines, fromfile=config_file, tofile=temp_file
        )
        result = "".join(diff)

        return result if result else "No differences found"

    class PicleConfig:
        pipe = PipeFunctionsModel
        outputter = Outputters.outputter_nested


class ConfigModel(BaseModel):
    """
    Base class for configuration management models.

    This class provides functionality to:

    - Load configuration from YAML files
    - Update nested configuration values through PICLE commands
    - Stage changes in a temp file before committing
    - Save committed configuration with rotating backups
    - Rollback to previous configuration versions

    Usage:
        1. Define your config structure as nested Pydantic models
        2. Create a config manager that inherits from ConfigModel
        3. Set config_file path via PicleConfig
        4. Use PICLE commands to update config values (staged in temp file)
        5. Use 'commit' to persist or 'clear-changes' to discard
    """

    show: ConfigModelShowCommands = Field(None, description="Show commands")
    commit: StrictBool = Field(
        None,
        description="Commit pending config changes",
        json_schema_extra={"function": "commit_config", "presence": True},
    )
    rollback: StrictInt = Field(
        None,
        description="Rollback to a backup version",
        json_schema_extra={"function": "rollback_config"},
    )
    erase_configuration: StrictBool = Field(
        None,
        description="Erase running configuration",
        json_schema_extra={"function": "erase_config", "presence": True},
        alias="erase-configuration",
    )
    clear_changes: StrictBool = Field(
        None,
        description="Discard uncommitted changes",
        json_schema_extra={"function": "clear_changes_config", "presence": True},
        alias="clear-changes",
    )

    class PicleConfig:
        config_file: str = "configuration.yaml"  # Default config file path
        backup_on_save: int = (
            5  # Number of backups history to keep (set to 0 to disable)
        )
        commit_hook: Optional[Callable] = None  # Optional function to call after commit

    @staticmethod
    def load_config(config_file: str) -> dict:
        """
        Load configuration from YAML file.

        :param config_file: Path to the configuration file
        :return: Loaded configuration dictionary
        """
        if not HAS_YAML:
            raise RuntimeError("PyYAML is required for config file operations")

        config_path = Path(config_file)

        if not config_path.exists():
            # Create directories and file if they don't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.touch(exist_ok=True)
            log.info(f"Created config file: {config_file}")
            config_data = {}
        else:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}

        return config_data

    @staticmethod
    def save_config(
        config_file: str, config_data: dict, backup_on_save: int = 5
    ) -> str:
        """
        Save configuration to YAML file with rotating backups.

        :param config_file: Path to the configuration file
        :param config_data: Configuration dictionary to save
        :param backup_on_save: Number of backup files to keep (0 to disable)
        :return: Status message
        """
        config_path = Path(config_file)

        # Create rotating backups if requested
        if backup_on_save and config_path.exists():
            # Remove the oldest backup if it exists
            oldest_backup = Path(f"{config_path}.old{backup_on_save}")
            if oldest_backup.exists():
                os.remove(oldest_backup)
                log.debug(f"Removed oldest backup: {oldest_backup}")

            # Rotate existing backups (old1 -> old2, old2 -> old3, etc.)
            for i in range(backup_on_save - 1, 0, -1):
                old_backup = Path(f"{config_path}.old{i}")
                new_backup = Path(f"{config_path}.old{i + 1}")
                if old_backup.exists():
                    shutil.move(str(old_backup), str(new_backup))
                    log.debug(f"Rotated backup: {old_backup} -> {new_backup}")

            # Create new .old1 backup from current file
            newest_backup = Path(f"{config_path}.old1")
            shutil.copy2(config_path, newest_backup)
            log.debug(f"Created new backup: {newest_backup}")

        # Save the new configuration
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                config_data, f, default_flow_style=False, sort_keys=True, indent=2
            )

        log.info(f"Saved config to {config_file}")

        return f"Saved config to {config_file}"

    @staticmethod
    def update_nested_value(data: dict, path: list, value: Any) -> dict:
        """
        Set a value in nested dictionary using path list.

        :param data: Dictionary to modify
        :param path: List of keys representing the path
        :param value: Value to set at the path
        :return: Modified dictionary
        """
        if not path:
            return data

        current = data
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                log.warning(
                    f"Cannot traverse path: {'.'.join(path)}, {key} is not a dict"
                )
                return data
            current = current[key]

        # If both current value and new value are dicts, merge them
        if isinstance(value, dict) and isinstance(current.get(path[-1]), dict):
            current[path[-1]] = {**current[path[-1]], **value}
        # If both current value and new value are lists, extend the list
        elif isinstance(value, list) and isinstance(current.get(path[-1]), list):
            current[path[-1]].extend(value)
        else:
            current[path[-1]] = value
        return data

    @staticmethod
    def get_command_path(command: list) -> list:
        """
        Extract the configuration path from parsed command segments.

        :param command: List of parsed command segment dicts
        :return: List of string path components
        """
        ret = []
        for item in command:
            if isinstance(item["parameter"], str):
                ret.append(item["parameter"])

        return ret

    @staticmethod
    def get_model_config(shell_command: list) -> dict:
        """
        Reconstruct model configuration by merging ConfigModel defaults
        with the command's root model PicleConfig.

        :param shell_command: The shell command context
        :return: Merged configuration dictionary
        """
        command_root_model = shell_command[0]["model"]

        # reconstruct model configuration
        model_config = {
            k: v
            for k, v in ConfigModel.PicleConfig.__dict__.items()
            if not k.startswith("_")
        }
        model_config.update(
            {
                k: v
                for k, v in command_root_model.PicleConfig.__dict__.items()
                if not k.startswith("_")
            }
        )
        return model_config

    @staticmethod
    def erase_config(shell_command: list, erase_configuration: bool = True) -> str:
        """
        Erase configuration and save empty config to temp file.

        :param shell_command: The shell command context
        :param erase_config: Presence flag (always True when invoked)
        :return: Status message
        """
        model_config = ConfigModel.get_model_config(shell_command)
        config_file = model_config["config_file"]
        temp_file = config_file + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            yaml.safe_dump({}, f, default_flow_style=False, sort_keys=True, indent=2)

        return "Configuration cleared (uncommitted). Use 'commit' to save or 'show changes' to review."

    @staticmethod
    def clear_changes_config(shell_command: list, clear_changes: bool = True) -> str:
        """
        Discard uncommitted changes by deleting the temp config file.

        :param shell_command: The shell command context
        :return: Status message
        """
        model_config = ConfigModel.get_model_config(shell_command)
        config_file = model_config["config_file"]
        temp_file = config_file + ".tmp"

        if not os.path.exists(temp_file):
            return "No uncommitted changes to discard"

        os.remove(temp_file)
        return "Uncommitted changes discarded"

    @staticmethod
    def commit_config(shell_command: list, commit: bool = True) -> str:
        """
        Commit pending changes - save temp config to the main config file and remove temp.

        :param shell_command: The shell command context
        :param commit: Presence flag (always True when invoked)
        :return: Status message
        """
        model_config = ConfigModel.get_model_config(shell_command)
        config_file = model_config["config_file"]
        backup_on_save = model_config.get("backup_on_save", 5)
        temp_file = config_file + ".tmp"

        if not Path(temp_file).exists():
            return "No uncommitted changes to commit"

        temp_content = ConfigModel.load_config(temp_file)
        ConfigModel.save_config(
            config_file, temp_content, backup_on_save=backup_on_save
        )
        os.remove(temp_file)

        if model_config.get("commit_hook"):
            try:
                model_config["commit_hook"]()
            except Exception as e:
                log.error(f"Commit hook execution failed: {e}")
                return f"Configuration committed with errors in commit hook: {e}"

        return "Configuration committed successfully"

    @staticmethod
    def rollback_config(shell_command: list, rollback: int) -> str:
        """
        Rollback to a backup version by loading .oldN file into temp config.

        :param shell_command: The shell command context
        :param rollback: Backup number to rollback to (1, 2, 3, ...)
        :return: Status message
        """
        model_config = ConfigModel.get_model_config(shell_command)
        config_file = model_config["config_file"]
        temp_file = config_file + ".tmp"
        backup_file = f"{config_file}.old{rollback}"

        if not Path(backup_file).exists():
            return f"Backup file not found: {backup_file}"

        backup_content = ConfigModel.load_config(backup_file)

        # save backup content to temp file for review before commit
        with open(temp_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                backup_content, f, default_flow_style=False, sort_keys=True, indent=2
            )

        return f"Loaded backup {backup_file} into temp config. Use 'commit' to apply or 'show changes' to review."

    @staticmethod
    def run(shell_command: list, **kwargs) -> str:
        """
        Run method for configuration operations.
        Saves changes to a temp file. Use 'commit' to persist to config file.

        :param shell_command: The shell command that triggered this run method
        :param kwargs: Field values collected from the command line
        :return: Status message
        """
        model_config = ConfigModel.get_model_config(shell_command)
        command_path = ConfigModel.get_command_path(shell_command)
        config_file = model_config["config_file"]
        temp_file = config_file + ".tmp"

        # load from temp file if it exists (accumulate changes), else from config file
        if Path(temp_file).exists():
            config_content = ConfigModel.load_config(temp_file)
        else:
            config_content = ConfigModel.load_config(config_file)

        # update configuration data
        ConfigModel.update_nested_value(config_content, command_path, kwargs)

        # save to temp file
        with open(temp_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                config_content, f, default_flow_style=False, sort_keys=True, indent=2
            )

        return "Configuration updated (uncommitted). Use 'commit' to save or 'show changes' to review."
