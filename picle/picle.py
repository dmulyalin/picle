"""
PICLE - Python Interactive Command Line Shells
==============================================

PICLE is a module to construct interactive command line shell
applications.

PICLE build on top of Python standard library CMD module and
uses Pydantic models to construct shell environments.
"""

import cmd
import logging
import enum
import traceback
import os
import platform

from typing import Callable, Union
from pydantic import ValidationError, Json
from pydantic._internal._model_construction import ModelMetaclass
from pydantic.fields import FieldInfo
from .utils import run_print_exception
from .models import MAN

log = logging.getLogger(__name__)


class FieldLooseMatchOnly(Exception):
    """
    Raised if parameter not in model's fields but some of the
    fields names starts with parameter.
    """


class FieldKeyError(Exception):
    """
    Raised if parameter not in model's fields and none of the
    fields names starts with parameter.
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

    def write(self, text: str) -> None:
        """
        Method to write output to stdout

        :param text: text output
        """
        if not isinstance(text, str):
            text = str(text)
        if not text.endswith(self.newline):
            self.stdout.write(text + self.newline)
        else:
            self.stdout.write(text)

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
        Helper function to save collected value into field values

        :param field: field dictionary
        :param value: value to save string
        :pram replace: replaces current field value with new value
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
        if isinstance(value, str):
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

    def _get_field_params(self, field: FieldInfo) -> dict:
        if isinstance(field, FieldInfo):
            if getattr(field, "json_schema_extra"):
                return field.json_schema_extra
        elif isinstance(field, dict):
            return self._get_field_params(field.get("field"))
        return {}

    def _collect_multiline(self, field: dict) -> None:
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
        Method to validate current model field values
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

    def extract_model_defaults(self, model) -> dict:
        ret = {}
        # extract default values from model fields
        for name, field in model.model_fields.items():
            # skip non Field references e.g. to other models
            if not isinstance(field, FieldInfo):
                continue
            # skip references to Callables
            if field.annotation is Callable:
                continue
            # skip required Fields
            if field.is_required():
                continue
            # ignore None default values
            if field.get_default() is None:
                continue
            ret[name] = field.get_default()

        return ret

    def defaults_update(self, model) -> None:
        self.shell_defaults.update(self.extract_model_defaults(model))

    def defaults_pop(self, model) -> None:
        for name in model.model_fields.keys():
            self.shell_defaults.pop(name, None)

    def defaults_set(self, model) -> None:
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
                # check if current model has pipe defined
                if hasattr(current_model["model"], "PicleConfig") and getattr(
                    current_model["model"].PicleConfig, "pipe", None
                ):
                    if current_model["model"].PicleConfig.pipe == "self":
                        # reference pipe model to current model
                        current_model = {
                            "model": current_model["model"],
                            "fields": [],
                            "parameter": parameter,
                        }
                    else:
                        # goto pipe model
                        current_model = {
                            "model": current_model["model"].PicleConfig.pipe,
                            "fields": [],
                            "parameter": parameter,
                        }
                    models = [current_model]
                    ret.append(models)
                else:
                    log.error(
                        f"'{current_model['model'].__name__}' does not support pipe handling"
                    )
                    break
            # collect json dictionary string
            elif parameter.strip().startswith("{") and current_field:
                value_items = [parameter]
                # collect further values
                while parameters:
                    parameter = parameters.pop(0)
                    value_items.append(parameter)
                    if parameter.strip().endswith("}"):
                        break
                value = " ".join(value_items)  # form value string
                self._save_collected_value(current_field, value)
            # collect json list string
            elif parameter.strip().startswith("[") and current_field:
                value_items = [parameter]
                # collect further values
                while parameters:
                    parameter = parameters.pop(0)
                    value_items.append(parameter)
                    if parameter.strip().endswith("]"):
                        break
                value = " ".join(value_items)  # form value string
                self._save_collected_value(current_field, value)
            # collect double quoted field value
            elif '"' in parameter and current_field:
                value_items = [parameter.replace('"', "")]
                # collect further values if first parameter not double quoted value e.g. "nrp1"
                if parameter.count('"') != 2:
                    while parameters:
                        parameter = parameters.pop(0)
                        value_items.append(parameter.replace('"', ""))
                        if '"' in parameter:
                            break
                value = " ".join(value_items)  # form value string
                self._save_collected_value(current_field, value)
            # collect single quoted field value
            elif "'" in parameter and current_field:
                value_items = [parameter.replace("'", "")]
                # collect further values if first parameter not double quoted value e.g. 'nrp1'
                if parameter.count("'") != 2:
                    while parameters:
                        parameter = parameters.pop(0)
                        value_items.append(parameter.replace("'", ""))
                        if "'" in parameter:
                            break
                value = " ".join(value_items)  # form value string
                self._save_collected_value(current_field, value)
            # handle reference to model
            elif current_model["model"].model_fields.get(parameter) or any(
                parameter == f.alias or parameter == f.serialization_alias
                for f in current_model["model"].model_fields.values()
            ):
                # source field by name
                if current_model["model"].model_fields.get(parameter):
                    field = current_model["model"].model_fields[parameter]
                else:
                    # source field by alias
                    for f_name, field in current_model["model"].model_fields.items():
                        if parameter == field.alias:
                            parameter = f_name  # use actual field name
                            break
                        elif parameter == field.serialization_alias:
                            parameter = f_name  # use actual field name
                            break
                # handle next level model reference
                if isinstance(field.annotation, ModelMetaclass):
                    # check need to record field presence before going to next model
                    if (
                        current_field.get("values") is ...
                        and current_field["field"].json_schema_extra is not None
                        and "presence" in current_field["field"].json_schema_extra
                    ):
                        value = current_field["field"].json_schema_extra["presence"]
                        self._save_collected_value(current_field, value)
                    # goto next model
                    current_model = {
                        "model": field.annotation,
                        "fields": [],
                        "parameter": parameter,
                    }
                    models.append(current_model)
                    current_field = {}  # empty current field
                    # extract first command default values from current model
                    if len(ret) == 1:
                        current_model["defaults"] = self.extract_model_defaults(
                            field.annotation
                        )
                # handle actual field reference
                elif isinstance(field, FieldInfo):
                    # check need to record field presence before going to next field
                    if (
                        current_field.get("values") is ...
                        and current_field["field"].json_schema_extra is not None
                        and "presence" in current_field["field"].json_schema_extra
                    ):
                        value = current_field["field"].json_schema_extra["presence"]
                        self._save_collected_value(current_field, value)
                    # goto next field
                    current_field = {"name": parameter, "values": ..., "field": field}
                    # find and replace default value if present
                    for index, field in enumerate(current_model["fields"]):
                        if field["name"] == current_field["name"]:
                            current_model["fields"][index] = current_field
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
                # check if last field has enum values equal to parameter
                if any(i.value == parameter for i in current_field["field"].annotation):
                    self._save_collected_value(current_field, parameter)
                # check if last field has enum values partially matching parameter
                elif any(
                    i.value.startswith(parameter)
                    for i in current_field["field"].annotation
                ):
                    raise FieldLooseMatchOnly(current_model, parameter)
            # check if parameter partially matches any of the model fields
            elif any(
                field_name.startswith(parameter)
                for field_name in current_model["model"].model_fields
            ):
                raise FieldLooseMatchOnly(current_model, parameter)
            # check if parameter partially matches any of the model fields' aliases
            elif any(
                field.alias.startswith(parameter)
                for field in current_model["model"].model_fields.values()
                if field.alias is not None
            ):
                raise FieldLooseMatchOnly(current_model, parameter)
            # check if parameter partially matches any of the model fields' serialization aliases
            elif any(
                field.serialization_alias.startswith(parameter)
                for field in current_model["model"].model_fields.values()
                if field.serialization_alias is not None
            ):
                raise FieldLooseMatchOnly(current_model, parameter)
            # parameter is a value, save it to current model
            elif current_field:
                self._save_collected_value(current_field, parameter)
            else:
                raise FieldKeyError(current_model, parameter)
        # check presence for last parameter is not is_help
        if (
            is_help is False
            and current_field.get("values") is ...
            and current_field["field"].json_schema_extra is not None
            and "presence" in current_field["field"].json_schema_extra
        ):
            value = current_field["field"].json_schema_extra["presence"]
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
        match: str = None,
        print_help: bool = True,
    ) -> None:
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
            field = model["model"].model_fields[last_field["name"]]
            json_schema_extra = getattr(field, "json_schema_extra") or {}
            name = f"<'{last_field['name']}' value>"
            # check if field is callable
            if field.annotation is Callable:
                name = "<ENTER>"
                lines[name] = "Execute command"
                width = max(width, len(name))
            # check if field referencing function
            elif json_schema_extra.get("function"):
                lines[name] = f"{field.description}"
                name = "<ENTER>"
                lines[name] = "Execute command"
                width = max(width, len(name))
            # add options for enumerations
            elif isinstance(field.annotation, enum.EnumMeta):
                options = [i.value for i in field.annotation]
                lines[name] = ", ".join(options)
            # check if model has method to source field choices
            elif hasattr(model["model"], f"source_{last_field['name']}"):
                options = getattr(model["model"], f"source_{last_field['name']}")()
                lines[name] = ", ".join(options)
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
                width = max(width, len(name))
            # iterate over model fields
            for name, field in model["model"].model_fields.items():
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
                width = max(width, len(name))
        # check if model has pipe defined
        if hasattr(model["model"], "PicleConfig") and getattr(
            model["model"].PicleConfig, "pipe", None
        ):
            name = "|"
            lines[name] = "Execute pipe command"
            width = max(width, len(name))
        width = max(width, len(name))
        # form help lines
        help_msg = []
        for k in sorted(lines.keys()):
            padding = " " * (width - len(k)) + (" " * 4)
            help_msg.append(f" {k}{padding}{lines[k]}")

        if print_help:  # print help message
            self.write(self.newline.join(help_msg))
        else:
            return help_msg, width

    def completedefault(self, text, line, begidx, endidx):
        """
        This method called for every  command parameter on
        complete key hit except for the very first one.
        """
        fieldnames = []
        try:
            command_models = self.parse_command(line, is_help=True)
            last_model = command_models[-1][-1]["model"]
            # check if last model has fields collected
            if command_models[-1][-1]["fields"]:
                last_field_name = command_models[-1][-1]["fields"][-1]["name"]
                last_field = last_model.model_fields[last_field_name]
                last_field_value = command_models[-1][-1]["fields"][-1]["values"]
                fparam = self._get_field_params(last_field)
                if isinstance(last_field_value, list):
                    last_field_value = last_field_value[-1]
                elif last_field_value == ...:
                    last_field_value = ""
                # check if need to extract enum values
                if line.endswith(" ") and isinstance(
                    last_field.annotation, enum.EnumMeta
                ):
                    fieldnames = [
                        i.value
                        for i in last_field.annotation
                        if i.value.startswith(last_field_value)
                        and i.value != last_field_value
                    ]
                # check if model has method to source field choices
                elif line.endswith(" ") and hasattr(
                    last_model, f"source_{last_field_name}"
                ):
                    fieldnames = getattr(last_model, f"source_{last_field_name}")()
                    fieldnames = [
                        i for i in fieldnames if i.startswith(last_field_value)
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
                for name, f in last_model.model_fields.items():
                    if f.alias:
                        fieldnames.append(f.alias)
                    if f.serialization_alias:
                        fieldnames.append(f.serialization_alias)
                    else:
                        fieldnames.append(name)
        except FieldLooseMatchOnly as e:
            model, parameter = e.args
            for name, f in model["model"].model_fields.items():
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
                        i.value for i in f.annotation if i.value.startswith(parameter)
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

        return sorted(fieldnames)

    def completenames(self, text, line, begidx, endidx):
        """
        This method only called for the very first command parameter on
        complete key hit.
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
            fieldnames.extend(command_models[-1][-1]["model"].model_fields)
        # collect arguments that startswith last parameter
        except FieldLooseMatchOnly as e:
            model, parameter = e.args
            for name, f in model["model"].model_fields.items():
                if f.alias and f.alias.startswith(parameter):
                    fieldnames.append(f.alias)
                elif f.serialization_alias and f.serialization_alias.startswith(
                    parameter
                ):
                    fieldnames.append(f.serialization_alias)
                elif name.startswith(parameter):
                    fieldnames.append(name)
        # raised if no model fields matched last parameter
        except FieldKeyError as e:
            log.debug(f"No model fields matched last parameter - {e}")
            pass
        return sorted(fieldnames)

    def do_help(self, arg):
        """Print help message"""
        command_models = self.parse_command(arg.strip("?"), is_help=True)
        help_msg, width = self.print_model_help(
            command_models,
            verbose=True if arg.strip().endswith("?") else False,
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
            # form help lines
            if lines:
                for k, v in lines.items():
                    padding = " " * (width - len(k)) + (" " * 4)
                    help_msg.append(f" {k}{padding}{v}")
                # print help message
                self.write(self.newline.join(help_msg))

    def do_exit(self, arg):
        """Exit current shell"""
        if "?" in arg:
            self.write(" exit    Exit current shell")
        else:
            # delete defaults for closing shell
            self.defaults_pop(self.shells[-1])
            _ = self.shells.pop(-1)
            if self.shells:
                self.shell = self.shells[-1]
                self.prompt = self.shell.PicleConfig.prompt
                if len(self.shells) == 1:  # check if reached top shell
                    self.defaults_set(self.shell)
            else:
                return True

    def do_top(self, arg):
        """Exit to top shell"""
        if "?" in arg:
            self.write(" top    Exit to top shell")
        else:
            self.shell = self.shells[0]
            self.prompt = self.shell.PicleConfig.prompt
            while self.shells:
                _ = self.shells.pop()
            self.shells.append(self.shell)
            # set shell defaults
            self.defaults_set(self.shell)

    def do_end(self, arg):
        """Exit application"""
        if "?" in arg:
            self.write(" end    Exit application")
        else:
            return True

    def do_pwd(self, arg):
        """Print current shell path"""
        if "?" in arg:
            self.write(" pwd    Print current shell path")
        else:
            path = ["Root"]
            for shell in self.shells[1:]:
                path.append(shell.__name__)
            self.write("->".join(path))

    def do_cls(self, arg):
        """Clear shell Screen"""
        if "?" in arg:
            self.write(" cls    Clear shell Screen")
        else:
            if "LINUX" in platform.system().upper():
                os.system("clear")
            elif "WINDOWS" in platform.system().upper():
                os.system("cls")

    @run_print_exception
    def default(self, line: str):
        """Method called if no do_xyz methods found"""
        ret = False
        outputter = None

        if line.strip().endswith("?"):
            try:
                command_models = self.parse_command(
                    line.strip().rstrip("?"), is_help=True
                )
            except FieldLooseMatchOnly as e:
                model, parameter = e.args
                self.print_model_help(
                    [[model]],
                    verbose=True if line.strip().endswith("??") else False,
                    match=parameter,
                )
            except FieldKeyError as e:
                model, parameter = e.args
                model_name = (
                    model["model"].__name__
                    if hasattr(model["model"], "__name__")
                    else model["model"].__repr_name__()
                )
                self.write(
                    f"Incorrect command, '{parameter}' not part of '{model_name}' model fields"
                )
            else:
                self.print_model_help(
                    command_models,
                    verbose=True if line.strip().endswith("??") else False,
                )
        else:
            try:
                command_models = self.parse_command(line, collect_multiline=True)
            except FieldLooseMatchOnly as e:
                model, parameter = e.args
                # filter fields to return message for
                fields = [
                    f.alias or f.serialization_alias or name
                    for name, f in model["model"].model_fields.items()
                    if name.startswith(parameter)
                ]
                self.write(
                    f"Incomplete command, possible completions: " f"{', '.join(fields)}"
                )
            except FieldKeyError as e:
                model, parameter = e.args
                model_name = (
                    model["model"].__name__
                    if hasattr(model["model"], "__name__")
                    else model["model"].__repr_name__()
                )
                self.write(
                    f"Incorrect command, '{parameter}' not part of '{model_name}' model fields"
                )
            except ValidationError as e:
                self.write(e)
            else:
                # go over collected commands separated by pipe
                for index, command in enumerate(command_models):
                    # collect arguments
                    command_arguments = {
                        f["name"]: f["values"]
                        for model in command
                        for f in model["fields"]
                        if f["values"] is not ...
                    }
                    # collect command defaults
                    command_defaults = {}
                    for model in command:
                        command_defaults.update(model.get("defaults", {}))
                    model = command[-1]["model"]
                    # check if model has subshell
                    if (
                        not command_arguments
                        and hasattr(model, "PicleConfig")
                        and getattr(model.PicleConfig, "subshell", None) is True
                    ):
                        # collect parent shells and defaults
                        for item in command[:-1]:
                            m = item["model"]
                            self.defaults_update(m)  # store shell defaults
                            if (
                                hasattr(m, "PicleConfig")
                                and getattr(m.PicleConfig, "subshell", None) is True
                            ):
                                if m not in self.shells:
                                    self.shells.append(m)
                        # update prompt value
                        self.prompt = getattr(model.PicleConfig, "prompt", self.prompt)
                        self.shell = model
                        self.shells.append(self.shell)
                    # run model "run" function if it exits
                    elif hasattr(model, "run"):
                        # validate command argument values
                        self._validate_values(command)
                        # call first command using collected arguments only
                        if index == 0:
                            kw = {
                                **self.shell_defaults,
                                **command_defaults,
                                **command_arguments,
                            }
                            ret = model.run(**kw)
                        # pipe results through subsequent commands
                        else:
                            kw = {
                                **command_defaults,
                                **command_arguments,
                            }
                            ret = model.run(ret, **kw)
                        # run processors from PicleConfig if any for first command only
                        if index == 0:
                            if hasattr(model, "PicleConfig") and hasattr(
                                model.PicleConfig, "processors"
                            ):
                                for processor in model.PicleConfig.processors:
                                    if callable(processor):
                                        ret = processor(ret)
                        # extract outputter from PicleConfig
                        if index == 0:
                            # check if outputter returned together with results
                            if isinstance(ret, tuple):
                                if len(ret) == 2:
                                    ret, outputter = ret
                                    outputter_kwargs = {}
                                elif len(ret) == 3:
                                    ret, outputter, outputter_kwargs = ret
                            elif hasattr(model, "PicleConfig") and hasattr(
                                model.PicleConfig, "outputter"
                            ):
                                outputter = model.PicleConfig.outputter
                                outputter_kwargs = getattr(
                                    model.PicleConfig, "outputter_kwargs", {}
                                )
                    # run command using Callable or json_schema_extra["function"]
                    elif command[-1]["fields"]:
                        # validate command argument values
                        self._validate_values(command)
                        # extract last field
                        last_field_name = command[-1]["fields"][-1]["name"]
                        last_field = model.model_fields[last_field_name]
                        json_schema_extra = (
                            getattr(last_field, "json_schema_extra") or {}
                        )
                        # check if last field refers to callable e.g. function
                        if last_field.annotation is Callable:
                            method_name = last_field.get_default()
                            if method_name and hasattr(model, method_name):
                                # call first command using collected arguments only
                                if index == 0:
                                    kw = {
                                        **self.shell_defaults,
                                        **command_defaults,
                                        **command_arguments,
                                    }
                                    # check if need to give root model as an argument
                                    if json_schema_extra.get("root_model"):
                                        kw["root_model"] = self.root
                                    # check if need to give PICLE App as an argument
                                    if json_schema_extra.get("picle_app"):
                                        kw["picle_app"] = self
                                    ret = getattr(model, method_name)(**kw)
                                # pipe results through subsequent commands
                                else:
                                    kw = {
                                        **command_defaults,
                                        **command_arguments,
                                    }
                                    ret = getattr(model, method_name)(ret, **kw)
                            else:
                                self.write(
                                    f"Model '{model.__name__}' has no '{method_name}' "
                                    f"method defined for '{last_field_name}' Callable field"
                                )
                        # check if last field has `function` parameter defined
                        elif json_schema_extra.get("function"):
                            method_name = json_schema_extra["function"]
                            if hasattr(model, method_name):
                                # call first command using collected arguments only
                                if index == 0:
                                    kw = {
                                        **self.shell_defaults,
                                        **command_defaults,
                                        **command_arguments,
                                    }
                                    # check if need to give root model as an argument
                                    if json_schema_extra.get("root_model"):
                                        kw["root_model"] = self.root
                                    # check if need to give PICLE App as an argument
                                    if json_schema_extra.get("picle_app"):
                                        kw["picle_app"] = self
                                    ret = getattr(model, method_name)(**kw)
                                # pipe results through subsequent commands
                                else:
                                    kw = {
                                        **command_defaults,
                                        **command_arguments,
                                    }
                                    ret = getattr(model, method_name)(ret, **kw)
                            else:
                                self.write(
                                    f"Model '{model.__name__}' has no '{method_name}' "
                                    f"method defined for '{last_field_name}' function"
                                )
                        else:
                            self.write(
                                f"Model '{model.__name__}' has no 'run' method defined"
                            )
                        # use processors from Field definition if any
                        if json_schema_extra.get("processors"):
                            for processor in json_schema_extra["processors"]:
                                if callable(processor):
                                    ret = processor(ret)
                        # run processors from PicleConfig if any for first command only
                        if index == 0:
                            if hasattr(model, "PicleConfig") and hasattr(
                                model.PicleConfig, "processors"
                            ):
                                for processor in model.PicleConfig.processors:
                                    if callable(processor):
                                        ret = processor(ret)
                        # extract outputter from first command
                        if index == 0:
                            # check if outputter returned together with results
                            if isinstance(ret, tuple):
                                if len(ret) == 2:
                                    ret, outputter = ret
                                    outputter_kwargs = {}
                                elif len(ret) == 3:
                                    ret, outputter, outputter_kwargs = ret
                            # use outputter from Field definition
                            elif json_schema_extra.get("outputter"):
                                outputter = json_schema_extra["outputter"]
                                outputter_kwargs = json_schema_extra.get(
                                    "outputter_kwargs", {}
                                )
                            # use PicleConfig outputter
                            elif hasattr(model, "PicleConfig") and hasattr(
                                model.PicleConfig, "outputter"
                            ):
                                outputter = model.PicleConfig.outputter
                                outputter_kwargs = getattr(
                                    model.PicleConfig, "outputter_kwargs", {}
                                )
                    else:
                        self.defaults_pop(model)
                        ret = f"Incorrect command, provide more arguments for '{model}' model"
                        break

        # returning True will end the shell - exit
        if ret is True:
            return True

        if ret:
            # use specified outputter to output results
            if callable(outputter):
                outputter(ret, **outputter_kwargs)
            # write to stdout by default
            else:
                self.write(ret)
