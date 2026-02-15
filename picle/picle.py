"""
PICLE - Python Interactive Command Line Shells
==============================================

PICLE is a module to construct interactive command line shell
applications.

PICLE is built on top of Python standard library CMD module and
uses Pydantic models to construct shell environments.
"""

import cmd
import logging
import enum
import traceback
import os
import platform
import inspect

from typing import Any, Optional, Union
from pydantic import ValidationError, Json
from pydantic._internal._model_construction import ModelMetaclass
from pydantic.fields import FieldInfo
from .utils import run_print_exception
from .models import MAN

try:
    from rich.console import Console as rich_console

    RICHCONSOLE = rich_console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

log = logging.getLogger(__name__)


def model_fields(model: Any) -> dict[str, FieldInfo]:
    """
    Access model_fields from the class to avoid Pydantic V2.11 deprecation
    warning about accessing model_fields on an instance.

    :param model: Pydantic model class or instance.
    :return: dictionary mapping field names to their ``FieldInfo`` objects.
    """
    if isinstance(model, type):
        return model.model_fields
    return type(model).model_fields


def callable_expects_argument(func: callable, arg_name: str) -> bool:
    """
    Check if a callable function expects a specific argument name.

    :param func: A callable (function, method, lambda, etc.).
    :param arg_name: The name of the argument to check for.
    :return: True if the callable expects the argument, False otherwise.
    """
    try:
        sig = inspect.signature(func)
        return arg_name in sig.parameters
    except (ValueError, TypeError):
        # Some built-in functions don't have inspectable signatures
        return False


class FieldLooseMatchOnly(Exception):
    """
    Raised when a parameter is not an exact match of any model field
    but one or more field names start with the parameter string.
    """


class FieldKeyError(Exception):
    """
    Raised when a parameter does not match any model field and none
    of the field names start with the parameter string.
    """


class App(cmd.Cmd):
    """
    PICLE App class to construct shell.

    :param root: Root/Top Pydantic model
    """

    ruler = ""
    intro = "PICLE APP"
    prompt = "picle#"
    newline = "\r\n"
    completekey = "tab"
    use_rich = True

    def __init__(self, root, stdin=None, stdout=None):
        self.root = root
        self.shell = self.root.model_construct()
        self.shell_defaults = {}
        self.shells = [self.shell]

        # extract configuration from shell model
        if hasattr(self.shell, "PicleConfig"):
            self.ruler = getattr(self.shell.PicleConfig, "ruler", self.ruler)
            self.intro = getattr(self.shell.PicleConfig, "intro", self.intro)
            self.prompt = getattr(self.shell.PicleConfig, "prompt", self.prompt)
            self.newline = getattr(self.shell.PicleConfig, "newline", self.newline)
            self.use_rich = getattr(self.shell.PicleConfig, "use_rich", self.use_rich)
            self.completekey = getattr(
                self.shell.PicleConfig, "completekey", self.completekey
            )

            # mount override methods
            if hasattr(self.shell.PicleConfig, "methods_override"):
                for (
                    method_name,
                    override,
                ) in self.shell.PicleConfig.methods_override.items():
                    setattr(self, method_name, getattr(self.shell, override))

        # mount models
        self.model_mount(MAN, ["man"], "Manual/documentation functions")

        super(App, self).__init__(stdin=stdin, stdout=stdout)

    def start(self) -> None:
        self.cmdloop()

    def emptyline(self) -> None:
        """Override empty line method to not run last command"""
        return None

    def write(self, output: str) -> None:
        """
        Method to write output to stdout

        :param output: output to write to stdout
        """
        if self.use_rich and HAS_RICH:
            RICHCONSOLE.print(output)
        else:
            if not isinstance(output, str):
                output = str(output)
            if not output.endswith(self.newline):
                output += self.newline
            self.stdout.write(output)

    def model_mount(
        self,
        model: ModelMetaclass,
        path: Union[str, list[str]],
        description: str = None,
        default=None,
        **kwargs: dict,
    ) -> None:
        """
        Method to mount pydantic model at provided path in relation to the root model.

        :param model: Pydantic model to mount.
        :param path: List of path segments to mount the model.
        :param description: Description of the model.
        :param default: Default value for the model.
        :param kwargs: Additional keyword arguments for the FieldInfo.
        """
        if isinstance(path, str):
            path = [path.strip()]
        parent_model = self.root
        while path:
            mount_name = path.pop(0)
            if mount_name in parent_model.model_fields:
                parent_model = parent_model.model_fields[mount_name].annotation
            else:
                # handle when not all path items before last one are in models tree
                if len(path) > 0:
                    raise KeyError(
                        f"'{mount_name}' not part of '{parent_model}' model fields, but remaining path still not empty - {path}"
                    )
                parent_model.model_fields[mount_name] = FieldInfo(
                    annotation=model,
                    required=False,
                    description=description,
                    default=default,
                    **kwargs,
                )
                break

    def model_remove(self, path: list[str]) -> None:
        """
        Method to remove pydantic model at provided path in relation to the root model.

        :param path: List of path segments to remove the model.
        """
        if isinstance(path, str):
            path = [path.strip()]
        parent_model = self.root
        while path:
            mount_name = path.pop(0)
            if mount_name in parent_model.model_fields:
                if len(path) == 0:
                    parent_model = parent_model.model_fields.pop(mount_name)
                else:
                    parent_model = parent_model.model_fields[mount_name].annotation
            else:
                raise KeyError(
                    f"Failed to remove model at path '{mount_name}', parent model: '{parent_model}'"
                )

    def _save_collected_value(
        self, field: dict, value: str, replace: bool = False
    ) -> None:
        """
        Helper function to save collected value into field values.

        :param field: field dictionary containing ``field``, ``values`` and ``name`` keys.
        :param value: value string to save.
        :param replace: if True, replaces the current field value with the new value.
        """
        # leave it as a string as it is Json field
        if field["field"].metadata and isinstance(field["field"].metadata[0], Json):
            # save single value
            if field["values"] == ...:
                field["values"] = value
            # append new value to the previous string
            else:
                field["values"] += value
            return

        # attempt to mutate value
        if field["field"].annotation is not str and isinstance(value, str):
            # convert value to boolean
            if value.title() == "False":
                value = False
            elif value.title() == "True":
                value = True
            elif value.title() == "None":
                value = None
            # convert to integer
            elif value.isdigit():
                value = int(value)
            # convert to float
            elif "." in value:
                try:
                    value = float(value)
                except ValueError:
                    pass

        # save single value
        if field["values"] == ...:
            field["values"] = value
        # replace current value
        elif replace:
            field["values"] = value
        # add further values
        elif isinstance(field["values"], list):
            field["values"].append(value)
        # transform values to a list if one value already collected
        else:
            field["values"] = [field.pop("values"), value]

    def _resolve_field(
        self, model: Any, parameter: str
    ) -> Optional[tuple[str, FieldInfo]]:
        """
        Resolve a parameter to a model field by name, alias, or serialization_alias.

        :param model: Pydantic model class or instance.
        :param parameter: parameter string to resolve.
        :return: tuple of (canonical_field_name, FieldInfo) or None.
        """
        fields = model_fields(model)
        if parameter in fields:
            return parameter, fields[parameter]
        for f_name, field in fields.items():
            if parameter == field.alias or parameter == field.serialization_alias:
                return f_name, field
        return None

    def _has_partial_match(self, model: Any, parameter: str) -> bool:
        """
        Check if parameter is a prefix of any field name, alias, or serialization_alias.

        :param model: Pydantic model class or instance.
        :param parameter: parameter string to check.
        :return: True if any field partially matches.
        """
        for name, field in model_fields(model).items():
            if name.startswith(parameter):
                return True
            if field.alias and field.alias.startswith(parameter):
                return True
            if field.serialization_alias and field.serialization_alias.startswith(
                parameter
            ):
                return True
        return False

    def _get_field_params(self, field: Union[FieldInfo, dict]) -> dict:
        """
        Extract ``json_schema_extra`` parameters from a field.

        :param field: a ``FieldInfo`` instance or a field dictionary.
        :return: dictionary of extra JSON-schema parameters, or an empty dict.
        """
        if isinstance(field, FieldInfo):
            if getattr(field, "json_schema_extra"):
                return field.json_schema_extra
        elif isinstance(field, dict):
            return self._get_field_params(field.get("field"))
        return {}

    def _collect_multiline(self, field: dict) -> None:
        """
        Prompt the user for multi-line input when the field supports it.

        If the field has ``multiline`` set to ``True`` in its JSON-schema
        extra parameters and its current value is the literal string
        ``"input"``, the user is prompted to enter lines until Ctrl+D.

        :param field: field dictionary with ``field`` and ``values`` keys.
        """
        fparam = self._get_field_params(field["field"])
        multiline_buffer = []
        if fparam.get("multiline") is True and field["values"] == "input":
            self.write("Enter lines and hit Ctrl+D to finish multi line input")
            while True:
                try:
                    line = input()
                except EOFError:
                    break
                else:
                    multiline_buffer.append(line)
            self._save_collected_value(field, "\n".join(multiline_buffer), replace=True)

    def _validate_values(self, models: list) -> None:
        """
        Validate current model field values against the root or current
        shell model.

        Aggregates field values collected from each model in *models*
        (processed in reverse order) and validates the resulting data
        dictionary against the appropriate Pydantic model.

        :param models: list of model dictionaries produced by :meth:`parse_command`.
        :raises ValidationError: when the collected data fails Pydantic validation.
        """
        data = {}
        for model in reversed(models):
            kwargs = {
                f["name"]: f["values"]
                for f in model["fields"]
                if f["values"] is not ...
            }
            data = {**data, **kwargs}
            if model["parameter"] is not ...:
                data = {model["parameter"]: data}
        log.debug(f"Validating collected data against root model, data: {data}")
        # validate against root model
        if len(self.shells) == 1:
            self.root(**data)
        # validate against current shell model
        else:
            self.shell(**data)

    def extract_model_defaults(self, model: Any) -> dict:
        """
        Extract non-None default values from a Pydantic model's fields.

        :param model: Pydantic model class or instance to extract defaults from.
        :return: dictionary mapping field names to their default values.
        """
        ret = {}
        # extract default values from model fields
        for name, field in model_fields(model).items():
            # skip non Field references e.g. to other models
            if not isinstance(field, FieldInfo):
                continue
            # skip required Fields
            if field.is_required():
                continue
            # ignore None default values
            if field.get_default() is None:
                continue
            default = field.get_default()
            # convert Enum defaults to their plain value
            if isinstance(default, enum.Enum):
                default = default.value
            ret[name] = default

        return ret

    def defaults_update(self, model: Any) -> None:
        """
        Merge the given model's default field values into :attr:`shell_defaults`.

        :param model: Pydantic model class or instance.
        """
        self.shell_defaults.update(self.extract_model_defaults(model))

    def defaults_pop(self, model: Any) -> None:
        """
        Remove the given model's field names from :attr:`shell_defaults`.

        :param model: Pydantic model class or instance.
        """
        for name in model_fields(model).keys():
            self.shell_defaults.pop(name, None)

    def defaults_set(self, model: Any) -> None:
        """
        Replace :attr:`shell_defaults` with the given model's defaults.

        Clears the existing defaults and populates them from *model*.

        :param model: Pydantic model class or instance.
        """
        self.shell_defaults.clear()
        self.defaults_update(model)

    def parse_command(
        self, command: str, collect_multiline: bool = False, is_help: bool = False
    ) -> list:
        """
        Function to parse command string and construct list of model
        references and fields values.

        :param command: command string to parse through
        :param is_help: indicates that parsing help command or tab completion command,
            if set to True disables ``presence`` argument handling for last field
        :param collect_multiline: enables multiple input collection for fields
        :return: returns a list of lists of dictionaries with collected models details
            each dictionary containing ``model``, ``fields`` and ``parameter`` keys.
        """
        current_model = {
            "model": self.shell,
            "fields": [],
            "parameter": ...,
            "defaults": self.extract_model_defaults(self.shell),
        }
        current_field = {}
        models = [current_model]
        parameters = [i for i in command.split(" ") if i.strip()]
        ret = [models]

        # iterate over command parameters and decide if its a reference
        # to a model or model's field value
        while parameters:
            parameter = parameters.pop(0)

            # handle pipe - "|"
            if parameter == "|":
                pipe_config = getattr(
                    getattr(current_model["model"], "PicleConfig", None),
                    "pipe",
                    None,
                )
                if not pipe_config:
                    log.error(
                        f"'{current_model['model'].__name__}' does not support pipe handling"
                    )
                    break
                # resolve pipe model
                if pipe_config == "self":
                    pipe_model = current_model["model"]
                # import pipe model from module path string
                elif isinstance(pipe_config, str):
                    # rpartition - returns a tuple of (before_last_dot, dot, after_last_dot)
                    module_path, _, class_name = pipe_config.rpartition(".")
                    module = __import__(module_path, fromlist=[""])
                    pipe_model = getattr(module, class_name)
                else:
                    pipe_model = pipe_config
                current_model = {
                    "model": pipe_model,
                    "fields": [],
                    "parameter": parameter,
                }
                models = [current_model]
                ret.append(models)

            # collect JSON dictionary or list string
            elif parameter.strip().startswith(("{", "[")) and current_field:
                close = "}" if parameter.strip().startswith("{") else "]"
                value_items = [parameter]
                while parameters:
                    parameter = parameters.pop(0)
                    value_items.append(parameter)
                    if parameter.strip().endswith(close):
                        break
                self._save_collected_value(current_field, " ".join(value_items))

            # collect quoted field value (single or double quotes)
            elif ('"' in parameter or "'" in parameter) and current_field:
                quote = '"' if '"' in parameter else "'"
                value_items = [parameter.replace(quote, "")]
                if parameter.count(quote) != 2:
                    while parameters:
                        parameter = parameters.pop(0)
                        value_items.append(parameter.replace(quote, ""))
                        if quote in parameter:
                            break
                self._save_collected_value(current_field, " ".join(value_items))

            # handle exact match to model field by name, alias, or serialization_alias
            elif resolved := self._resolve_field(current_model["model"], parameter):
                parameter, field = resolved
                # record presence for previous field before moving on
                if current_field.get(
                    "values"
                ) is ... and "presence" in current_field.get("json_schema_extra", {}):
                    self._save_collected_value(
                        current_field,
                        current_field["json_schema_extra"]["presence"],
                    )
                # handle next level model reference
                if isinstance(field.annotation, ModelMetaclass):
                    current_model = {
                        "model": field.annotation,
                        "fields": [],
                        "parameter": parameter,
                    }
                    models.append(current_model)
                    current_field = {}
                    if len(ret) == 1:
                        current_model["defaults"] = self.extract_model_defaults(
                            field.annotation
                        )
                # handle actual field reference
                elif isinstance(field, FieldInfo):
                    current_field = {
                        "name": parameter,
                        "values": ...,
                        "field": field,
                        "json_schema_extra": field.json_schema_extra or {},
                    }
                    # find and replace default value if present
                    for idx, f in enumerate(current_model["fields"]):
                        if f["name"] == current_field["name"]:
                            current_model["fields"][idx] = current_field
                            break
                    else:
                        current_model["fields"].append(current_field)
                else:
                    raise TypeError(
                        f"Unsupported pydantic field type: '{type(field.annotation)}', "
                        f"parameter: '{parameter}', command: '{command}', current model: "
                        f"'{current_model['model']}'"
                    )

            # check if last field is an Enumerator
            elif current_field and isinstance(
                current_field["field"].annotation, enum.EnumMeta
            ):
                if any(
                    str(i.value) == parameter for i in current_field["field"].annotation
                ):
                    self._save_collected_value(current_field, parameter)
                elif any(
                    str(i.value).startswith(parameter)
                    for i in current_field["field"].annotation
                ):
                    raise FieldLooseMatchOnly(current_model, parameter)

            # check if parameter partially matches any model field
            elif self._has_partial_match(current_model["model"], parameter):
                raise FieldLooseMatchOnly(current_model, parameter)

            # parameter is a value, save it to current field
            elif current_field:
                self._save_collected_value(current_field, parameter)
            else:
                raise FieldKeyError(current_model, parameter)
        # check presence for last parameter is not is_help
        if (
            is_help is False
            and current_field.get("values") is ...
            and "presence" in current_field["json_schema_extra"]
        ):
            value = current_field["json_schema_extra"]["presence"]
            self._save_collected_value(current_field, value)

        # iterate over collected models and fields to see
        # if need to collect multi-line input
        if collect_multiline:
            for command_models in ret:
                for model in command_models:
                    for field in model["fields"]:
                        self._collect_multiline(field)

        return ret

    def print_model_help(
        self,
        models: list,
        verbose: bool = False,
        match: Optional[str] = None,
        print_help: bool = True,
    ) -> Optional[tuple[list[str], int]]:
        """
        Function to form and print help message for model fields.

        :param match: only collect help for fields that start with ``match`` string
        :param print_help: if true prints help, return tuple of help lines
            list and width of longest line
        """
        model = models[-1][-1]  # get last model
        last_field = model["fields"][-1] if model["fields"] else None
        fparam = self._get_field_params(last_field)
        lines = {}  # dict of {cmd: cmd_help}
        width = 0  # record longest command width for padding
        # print help message only for last collected field
        if last_field and last_field["values"] == ...:
            field = last_field["field"]
            json_schema_extra = last_field["json_schema_extra"]
            name = f"<'{last_field['name']}' value>"
            # check if field referencing function
            if json_schema_extra.get("function"):
                lines[name] = f"{field.description}"
                name = "<ENTER>"
                lines[name] = "Execute command"
            # add options for enumerations
            elif isinstance(field.annotation, enum.EnumMeta):
                options = [i.value for i in field.annotation]
                lines[name] = ", ".join([str(i) for i in options])
            # check if model has method to source field choices
            elif hasattr(model["model"], f"source_{last_field['name']}"):
                options = getattr(model["model"], f"source_{last_field['name']}")()
                lines[name] = ", ".join([str(i) for i in options])
            else:
                lines[name] = f"{field.description}"
                # check if field supports multiline input
                if fparam.get("multiline") is True:
                    lines["input"] = "Collect value using multi line input mode"
                if verbose:
                    lines[name] += (
                        f"; default '{field.get_default()}', type '{str(field.annotation)}', "
                        f"is required - {field.is_required()}"
                    )
        # collect help message for all fields of this model
        else:
            # check if model supports subshell
            if (
                hasattr(model["model"], "PicleConfig")
                and getattr(model["model"].PicleConfig, "subshell", None) is True
                # exclude <ENTER> if already in model's shell
                and not self.shells[-1] == model["model"]
            ):
                name = "<ENTER>"
                lines[name] = "Enter command subshell"
            # iterate over model fields
            for name, field in model_fields(model["model"]).items():
                # skip fields that already have values
                if any(f["name"] == name for f in model["fields"]):
                    continue
                # check if field has alias
                if field.alias:
                    name = field.alias
                # check if field has serialization alias
                if field.serialization_alias:
                    name = field.serialization_alias
                # filter fields
                if match and not name.startswith(match):
                    continue
                lines[name] = f"{field.description}"
                if verbose:
                    lines[name] += (
                        f"; default '{field.get_default()}', type '{str(field.annotation)}', "
                        f"is required - {field.is_required()}"
                    )
        # check if model has pipe defined
        if hasattr(model["model"], "PicleConfig") and getattr(
            model["model"].PicleConfig, "pipe", None
        ):
            name = "|"
            lines[name] = "Execute pipe command"
        width = max((len(k) for k in lines), default=width)
        # form help lines
        help_msg = []
        for k in sorted(lines.keys()):
            padding = " " * (width - len(k)) + (" " * 4)
            help_msg.append(f" {k}{padding}{lines[k]}")

        if print_help:  # print help message
            self.write(self.newline.join(help_msg))
        else:
            return help_msg, width

    def completedefault(
        self, text: str, line: str, begidx: int, endidx: int
    ) -> list[str]:
        """
        Return completions for every command parameter after the first one.

        Called by :mod:`cmd` on a tab-key hit for arguments beyond the
        initial command keyword.
        """
        fieldnames = []
        try:
            command_models = self.parse_command(line, is_help=True)
            last_model = command_models[-1][-1]["model"]
            # check if last model has fields collected
            if command_models[-1][-1]["fields"]:
                last_field_name = command_models[-1][-1]["fields"][-1]["name"]
                last_field = model_fields(last_model)[last_field_name]
                last_field_value = command_models[-1][-1]["fields"][-1]["values"]
                fparam = self._get_field_params(last_field)
                if isinstance(last_field_value, list):
                    last_field_value = last_field_value[-1]
                elif last_field_value == ...:
                    last_field_value = ""
                # check if need to extract enum values
                if isinstance(last_field.annotation, enum.EnumMeta):
                    fieldnames = [
                        str(i.value)
                        for i in last_field.annotation
                        if str(i.value).startswith(last_field_value)
                        and i.value != last_field_value
                    ]
                # check if model has method to source field choices
                elif hasattr(last_model, f"source_{last_field_name}"):
                    fieldnames = getattr(last_model, f"source_{last_field_name}")()
                    # handle partial match
                    if last_field_value not in fieldnames:
                        fieldnames = [
                            str(i)
                            for i in fieldnames
                            if str(i).startswith(last_field_value)
                        ]
                    # remove already collected values from choice
                    collected_values = command_models[-1][-1]["fields"][-1]["values"]
                    if collected_values is not ...:
                        fieldnames = [
                            i for i in fieldnames if i not in collected_values
                        ]
                # auto complete 'input' for multi-line input mode
                elif fparam.get("multiline") is True:
                    if (
                        "input".startswith(last_field_value)
                        and last_field_value != "input"
                    ):
                        fieldnames = ["input"]
            # return a list of all model fields
            else:
                if line.endswith(" "):
                    for name, f in model_fields(last_model).items():
                        if f.alias:
                            fieldnames.append(f.alias)
                        elif f.serialization_alias:
                            fieldnames.append(f.serialization_alias)
                        else:
                            fieldnames.append(name)
                else:
                    last_fieldname = command_models[-1][-1]["parameter"]
                    fieldnames.append(last_fieldname)
        except FieldLooseMatchOnly as e:
            model, parameter = e.args
            for name, f in model_fields(model["model"]).items():
                # skip fields with already collected values from complete prompt
                if any(
                    collected_field["name"] == name
                    for collected_field in model["fields"]
                    if collected_field["values"] is not ...
                ):
                    continue
                # handle Enum fields options
                elif any(
                    collected_field["name"] == name
                    for collected_field in model["fields"]
                ) and isinstance(f.annotation, enum.EnumMeta):
                    fieldnames = [
                        str(i.value)
                        for i in f.annotation
                        if str(i.value).startswith(parameter)
                    ]
                    break
                elif f.alias and f.alias.startswith(parameter):
                    fieldnames.append(f.alias)
                elif f.serialization_alias and f.serialization_alias.startswith(
                    parameter
                ):
                    fieldnames.append(f.serialization_alias)
                elif name.startswith(parameter):
                    fieldnames.append(name)
        except FieldKeyError:
            pass
        except:
            tb = traceback.format_exc()
            self.write(tb)

        return sorted([f"{i} " for i in fieldnames])

    def completenames(
        self, text: str, line: str, begidx: int, endidx: int
    ) -> list[str]:
        """
        Return completions for the very first command parameter.

        Called by :mod:`cmd` on a tab-key hit for the initial keyword.
        """
        fieldnames = []
        # collect global methods
        for method_name in dir(self):
            if method_name.startswith("do_"):
                name = method_name.replace("do_", "")
                if name.startswith(line):
                    fieldnames.append(name)
        # collect model arguments
        try:
            command_models = self.parse_command(line, is_help=True)
            fieldnames.extend(model_fields(command_models[-1][-1]["model"]))
        except FieldLooseMatchOnly as e:
            model, parameter = e.args
            for name, f in model_fields(model["model"]).items():
                display = f.alias or f.serialization_alias or name
                if display.startswith(parameter):
                    fieldnames.append(display)
        except FieldKeyError:
            pass
        return sorted([f"{i} " for i in fieldnames])

    def do_help(self, arg: str) -> None:
        """Print help message for the given command or model."""
        try:
            command_models = self.parse_command(arg.strip("?"), is_help=True)
        except FieldLooseMatchOnly as e:
            model, parameter = e.args
            self.print_model_help([[model]], verbose=..., match=parameter)
            return
        except FieldKeyError as e:
            model, parameter = e.args
            self.write(
                f"Incorrect command, '{parameter}' not part of "
                f"'{self._get_model_name(model)}' model fields"
            )
            return
        help_msg, width = self.print_model_help(
            command_models,
            verbose=arg.strip().endswith("?"),
            print_help=False,
        )
        # print help for global top commands
        if len(arg.strip().split(" ")) == 1:
            lines = {}  # dict of {cmd: cmd_help}
            for method_name in dir(self):
                if method_name.startswith("do_"):
                    name = method_name.replace("do_", "")
                    lines[name] = getattr(self, method_name).__doc__
                    width = max(width, len(name))
            if lines:
                for k, v in lines.items():
                    padding = " " * (width - len(k)) + (" " * 4)
                    help_msg.append(f" {k}{padding}{v}")
        self.write(self.newline.join(help_msg))

    def do_exit(self, arg: str) -> Optional[bool]:
        """Exit current shell or terminate if at the top level."""
        if "?" in arg:
            self.write(" exit    Exit current shell")
        else:
            # delete defaults for closing shell
            self.defaults_pop(self.shells[-1])
            _ = self.shells.pop(-1)
            if self.shells:
                self.shell = self.shells[-1]
                if hasattr(self.shell, "PicleConfig") and getattr(
                    self.shell.PicleConfig, "prompt"
                ):
                    self.prompt = self.shell.PicleConfig.prompt
                if len(self.shells) == 1:  # check if reached top shell
                    self.defaults_set(self.shell)
            else:
                return True

    def do_top(self, arg: str) -> None:
        """Exit to top shell, resetting the shell stack."""
        if "?" in arg:
            self.write(" top    Exit to top shell")
        else:
            self.shell = self.shells[0]
            if hasattr(self.shell, "PicleConfig") and getattr(
                self.shell.PicleConfig, "prompt"
            ):
                self.prompt = self.shell.PicleConfig.prompt
            while self.shells:
                _ = self.shells.pop()
            self.shells.append(self.shell)
            # set shell defaults
            self.defaults_set(self.shell)

    def do_end(self, arg: str) -> Optional[bool]:
        """Exit the application entirely."""
        if "?" in arg:
            self.write(" end    Exit application")
        else:
            return True

    def do_pwd(self, arg: str) -> None:
        """Print the current shell path from root."""
        if "?" in arg:
            self.write(" pwd    Print current shell path")
        else:
            path = ["Root"]
            for shell in self.shells[1:]:
                path.append(shell.__name__)
            self.write("->".join(path))

    def do_cls(self, arg: str) -> None:
        """Clear the terminal screen."""
        if "?" in arg:
            self.write(" cls    Clear shell Screen")
        else:
            if "LINUX" in platform.system().upper():
                os.system("clear")
            elif "WINDOWS" in platform.system().upper():
                os.system("cls")

    def _get_model_name(self, model) -> str:
        """Get display name for a model dict's model value."""
        m = model["model"]
        return m.__name__ if hasattr(m, "__name__") else m.__repr_name__()

    def _find_parent_run(self, command: list) -> callable:
        """
        Backtrace through parent models (in reverse order) to find one with
        a 'run' method defined.

        :param command: list of model dicts from parse_command, where earlier
            indices are parent models and later indices are child models.
        :return: tuple of (model, method_name, json_schema_extra, command_arguments)
            or None if no executable parent found.
        """
        # Iterate through models in reverse order (child to parent)
        for model_dict in reversed(command):
            model = model_dict["model"]
            if hasattr(model, "run"):
                return getattr(model, "run")

        return None

    def process_help_command(self, line: str) -> None:
        """
        Process inline help triggered by '?' or '??' at the end of a command line.

        :param line: input command line string ending with '?' or '??'.
        """
        verbose = line.endswith("??")
        try:
            command_models = self.parse_command(line.rstrip("?"), is_help=True)
        except FieldLooseMatchOnly as e:
            model, parameter = e.args
            self.print_model_help([[model]], verbose=verbose, match=parameter)
        except FieldKeyError as e:
            model, parameter = e.args
            self.write(
                f"Incorrect command, '{parameter}' not part of "
                f"'{self._get_model_name(model)}' model fields"
            )
        else:
            self.print_model_help(command_models, verbose=verbose)

    @run_print_exception
    def default(self, line: str) -> Optional[bool]:
        """Process a command line when no matching ``do_*`` method is found."""
        ret = False
        outputter = True  # use default outputter - self.write
        outputter_kwargs = {}
        line = line.strip()

        if line.endswith("?"):
            self.process_help_command(line)
        else:
            try:
                command_models = self.parse_command(line, collect_multiline=True)
            except FieldLooseMatchOnly as e:
                model, parameter = e.args
                fields = [
                    f.alias or f.serialization_alias or name
                    for name, f in model_fields(model["model"]).items()
                    if name.startswith(parameter)
                    or (f.alias and f.alias.startswith(parameter))
                    or (
                        f.serialization_alias
                        and f.serialization_alias.startswith(parameter)
                    )
                ]
                self.write(
                    f"Incomplete command, possible completions: {', '.join(fields)}"
                )
            except FieldKeyError as e:
                model, parameter = e.args
                self.write(
                    f"Incorrect command, '{parameter}' not part of "
                    f"'{self._get_model_name(model)}' model fields"
                )
            except ValidationError as e:
                self.write(e)
            else:
                # go over collected commands separated by pipe
                for index, command in enumerate(command_models):
                    json_schema_extra = {}
                    method_name = None
                    # collect arguments
                    command_arguments = {
                        f["name"]: f["values"]
                        for model in command
                        for f in model["fields"]
                        if f["values"] is not ...
                    }
                    # collect command defaults
                    command_defaults = {}
                    for cmd in command:
                        command_defaults.update(cmd.get("defaults", {}))
                    model = command[-1]["model"]
                    picle_config = getattr(model, "PicleConfig", None)

                    # check if model has subshell and no arguments provided - enter subshell
                    if (
                        not command_arguments
                        and getattr(picle_config, "subshell", None) is True
                    ):
                        for item in command[:-1]:
                            m = item["model"]
                            self.defaults_update(m)
                            if (
                                getattr(
                                    getattr(m, "PicleConfig", None), "subshell", None
                                )
                                is True
                                and m not in self.shells
                            ):
                                self.shells.append(m)
                        self.prompt = getattr(picle_config, "prompt", self.prompt)
                        self.shell = model
                        self.shells.append(self.shell)
                        continue

                    # resolve run function - prefer json_schema_extra "function", fallback to "run" method, search parents for "run"
                    if command[-1]["fields"]:
                        json_schema_extra = command[-1]["fields"][-1][
                            "json_schema_extra"
                        ]
                    if callable(json_schema_extra.get("function")):
                        run_function = json_schema_extra["function"]
                    else:
                        method_name = json_schema_extra.get("function", "run")
                        if hasattr(model, method_name):
                            run_function = getattr(model, method_name)
                        elif method_name != "run":
                            ret = f"Model '{model.__name__}' has no '{method_name}' method defined"
                            break
                        elif json_schema_extra.get("use_parent_run", True):
                            run_function = self._find_parent_run(command)
                            if run_function is None:
                                self.defaults_pop(model)
                                ret = f"Incorrect command for '{model.__name__}', model parents have no 'run' method to execute command"
                                break
                        else:
                            self.defaults_pop(model)
                            ret = f"Incorrect command for '{model.__name__}', model has no method to execute command"
                            break

                    self._validate_values(command)

                    # build kwargs and call the method
                    if index == 0:
                        kw = {
                            **self.shell_defaults,
                            **command_defaults,
                            **command_arguments,
                        }
                        if json_schema_extra.get("root_model"):
                            kw["root_model"] = self.root
                        if json_schema_extra.get("picle_app"):
                            kw["picle_app"] = self
                        if callable_expects_argument(run_function, "shell_command"):
                            kw["shell_command"] = command
                        ret = run_function(**kw)
                    else:
                        kw = {**command_defaults, **command_arguments}
                        if callable_expects_argument(run_function, "shell_command"):
                            kw["shell_command"] = command
                        ret = run_function(ret, **kw)

                    # apply field-level processors
                    for processor in json_schema_extra.get("processors", []):
                        if callable(processor):
                            ret = processor(ret)

                    # apply PicleConfig processors for first command only
                    if index == 0:
                        for processor in getattr(picle_config, "processors", []):
                            if callable(processor):
                                ret = processor(ret)

                    # resolve outputter: from return tuple, field definition, or PicleConfig
                    if isinstance(ret, tuple) and len(ret) == 2:
                        ret, outputter = ret
                        outputter_kwargs = {}
                    elif isinstance(ret, tuple) and len(ret) == 3:
                        ret, outputter, outputter_kwargs = ret
                    elif json_schema_extra.get("outputter"):
                        outputter = json_schema_extra["outputter"]
                        outputter_kwargs = json_schema_extra.get("outputter_kwargs", {})
                    elif picle_config and hasattr(picle_config, "outputter"):
                        outputter = picle_config.outputter
                        outputter_kwargs = getattr(picle_config, "outputter_kwargs", {})

        # returning True will end the shell - exit
        if ret is True:
            return True

        if ret:
            if callable(outputter):
                self.write(outputter(ret, **outputter_kwargs))
            elif outputter is True:
                self.write(ret)
