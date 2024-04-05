"""
PICLE - Python Interactive Command Line Shells
==============================================

PICLE is a module to construct interactive command line shell
applications.

PICLE build on top of Python standart library CMD module and 
uses Pydantic models to construct shell environments.
"""
import cmd
import logging
import enum
import traceback

from typing import Callable
from pydantic import ValidationError
from pydantic._internal._model_construction import ModelMetaclass
from pydantic.fields import FieldInfo


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


class SyntaxError(Exception):
    """
    Command syntax error
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
            for mount, override in self.shell.PicleConfig.methods_override.items():
                setattr(self, mount, getattr(self.shell, override))

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

    def _save_collected_value(self, field: dict, value: str) -> None:
        """
        Helper function to save collected value into field values

        :param field: field dictionary
        :param value: value to save string
        """
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
        # add further values
        elif isinstance(field["values"], list):
            field["values"].append(value)
        # transform values to a list if one value already collected
        else:
            field["values"] = [field.pop("values"), value]

    def _validate_values(self, models: list) -> None:
        """
        Method to validate current model field values
        """
        data = {}
        for model in reversed(models[1:]):
            kwargs = {
                f["name"]: f["values"]
                for f in model["fields"]
                if f["values"] is not ...
            }
            data = {model["parameter"]: {**data, **kwargs}}
        log.debug(f"Validating collected data against root model, data: {data}")
        # validate against root model
        if len(self.shells) == 1:
            self.root(**data)
        # validate against current shell model
        else:
            self.shell(**data)

    def parse_command(
        self, command: str, validate: bool = False, add_default_values: bool = False
    ) -> list:
        """
        Function to parse command string and construct list of model
        references and fields values.

        :param command: command string

        Returns a list of lists of dictionaries with collected models details
        each dictionary containing ``model``, ``fields`` and ``parameter``
        keys.
        """
        current_model = {"model": self.shell, "fields": [], "parameter": ...}
        current_field = {}
        models = [current_model]
        parameters = [i for i in command.split(" ") if i.strip()]
        pipe_models = None
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
                    raise SyntaxError(
                        f"'{current_model['model']}' does not support pipe handling"
                    )
            # collect single quoted field value
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
            # handle reference to model
            elif current_model["model"].model_fields.get(parameter) or any(
                parameter == f.alias
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
                # handle next level model reference
                if isinstance(field.annotation, ModelMetaclass):
                    # goto next model
                    current_model = {
                        "model": field.annotation,
                        "fields": [],
                        "parameter": parameter,
                    }
                    models.append(current_model)
                    current_field = {}  # empty current field
                    # extract default values from the current model
                    if add_default_values:
                        for f_name, f_value in current_model[
                            "model"
                        ].model_fields.items():
                            # skip references to other models
                            if not isinstance(f_value, FieldInfo):
                                continue
                            # skip references to callables
                            if f_value.annotation is Callable:
                                continue
                            # add field default value
                            if f_value.get_default() is not None:
                                current_model["fields"].append(
                                    {"name": f_name, "values": f_value.get_default()}
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
            # check if parameter value partially matches any of the model fields
            elif any(
                field.startswith(parameter)
                for field in current_model["model"].model_fields
            ):
                raise FieldLooseMatchOnly(current_model, parameter)
            # parameter is a value, save it to current model
            elif current_field:
                self._save_collected_value(current_field, parameter)
            else:
                raise FieldKeyError(current_model, parameter)
        # check presence for last parameter
        if (
            current_field.get("values") is ...
            and current_field["field"].json_schema_extra is not None
            and "presence" in current_field["field"].json_schema_extra
        ):
            value = current_field["field"].json_schema_extra["presence"]
            self._save_collected_value(current_field, value)
        # validated collected values
        if validate:
            self._validate_values(models)

        return ret

    def print_model_help(
        self, models: list, verbose: bool = False, match: str = None
    ) -> None:
        """
        Function to form and print help message for model fields.

        :param match: only collect help for fields that start with ``match`` string
        """
        model = models[-1][-1]  # get last model
        last_field = model["fields"][-1] if model["fields"] else None
        lines = {}  # dict of {cmd: cmd_help}
        width = 0  # record longest command width for padding
        # print help message only for last collected field
        if last_field and last_field["values"] == ...:
            field = model["model"].model_fields[last_field["name"]]
            name = f"<'{last_field['name']}' value>"
            # check if field is callable
            if field.annotation is Callable:
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
                # check if field has alias
                if field.alias:
                    name = field.alias
                # skip fields that already have values
                if any(f["name"] == name for f in model["fields"]):
                    continue
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
            help_msg.append(f"{k}{padding}{lines[k]}")
        # print help message
        self.write(self.newline.join(help_msg))

    def completedefault(self, text, line, begidx, endidx):
        """
        This method called for every  command parameter on
        complete key hit except for the very first one.
        """
        fieldnames = []
        try:
            command_models = self.parse_command(line)
            last_model = command_models[-1][-1]["model"]
            # check if last model has fields collected
            if command_models[-1][-1]["fields"]:
                last_field_name = command_models[-1][-1]["fields"][-1]["name"]
                last_field = last_model.model_fields[last_field_name]
                last_field_value = command_models[-1][-1]["fields"][-1]["values"]
                if isinstance(last_field_value, list):
                    last_field_value = last_field_value[-1]
                elif last_field_value == ...:
                    last_field_value = ""
                # check if need to extract enum values
                if isinstance(last_field.annotation, enum.EnumMeta):
                    fieldnames = [
                        i.value
                        for i in last_field.annotation
                        if i.value.startswith(last_field_value)
                    ]
                # check if model has method to source field choices
                elif hasattr(last_model, f"source_{last_field_name}"):
                    fieldnames = getattr(last_model, f"source_{last_field_name}")()
                    fieldnames = [
                        i for i in fieldnames if i.startswith(last_field_value)
                    ]
            # return a list of all model fields
            else:
                fieldnames = list(last_model.model_fields)
        except FieldLooseMatchOnly as e:
            model, parameter = e.args
            fieldnames = [
                f.alias or name
                for name, f in model["model"].model_fields.items()
                # skip fields with already collected values from complete prompt
                if name.startswith(parameter)
                and not any(
                    True
                    for collected_field in model["fields"]
                    if collected_field["name"] == name
                    and collected_field["values"] is not ...
                )
            ]
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
            command_models = self.parse_command(line)
            fieldnames.extend(command_models[-1][-1]["model"].model_fields)
        # collect arguments that startswith last parameter
        except FieldLooseMatchOnly as e:
            model, parameter = e.args
            for name, f in model["model"].model_fields.items():
                if name.startswith(parameter):
                    fieldnames.append(name)
        # raised if no model fields matched last parameter
        except FieldKeyError as e:
            pass
        return sorted(fieldnames)

    def do_help(self, arg):
        """Print help message"""
        command_models = self.parse_command(arg.strip("?"))
        self.print_model_help(
            command_models, verbose=True if arg.strip().endswith("?") else False
        )
        # print help for global top commands
        if len(arg.strip().split(" ")) == 1:
            lines = {}  # dict of {cmd: cmd_help}
            width = 0  # record longest command width for padding
            for method_name in dir(self):
                if method_name.startswith("do_"):
                    name = method_name.replace("do_", "")
                    lines[name] = getattr(self, method_name).__doc__
                    width = max(width, len(name))
            # form help lines
            if lines:
                help_msg = []
                for k, v in lines.items():
                    padding = " " * (width - len(k)) + (" " * 4)
                    help_msg.append(f"{k}{padding}{v}")
                # print help message
                self.write(self.newline.join(help_msg))

    def do_exit(self, arg):
        """Exit current shell"""
        _ = self.shells.pop(-1)
        if self.shells:
            self.shell = self.shells[-1]
            self.prompt = self.shell.PicleConfig.prompt
        else:
            return True

    def do_top(self, arg):
        """Exit to top shell"""
        self.shell = self.shells[0]
        self.prompt = self.shell.PicleConfig.prompt
        while self.shells:
            _ = self.shells.pop()
        self.shells.append(self.shell)

    def do_end(self, arg):
        """Exit application"""
        return True

    def do_pwd(self, arg):
        """Print current shell path"""
        path = ["Root"]
        for shell in self.shells[1:]:
            path.append(shell.__name__)
        self.write("->".join(path))

    def default(self, line: str):
        """Method called if no do_xyz methods found"""
        ret = False

        # print help for given command or commands
        if line.strip().endswith("?"):
            try:
                command_models = self.parse_command(line.strip().rstrip("?"))
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
                command_models = self.parse_command(
                    line, validate=True, add_default_values=True
                )
            except FieldLooseMatchOnly as e:
                model, parameter = e.args
                # filter fields to return message for
                fields = [
                    f.alias or name
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
                    run_kwargs = {
                        f["name"]: f["values"]
                        for model in command
                        for f in model["fields"]
                        if f["values"] is not ...
                    }
                    # run model "run" function if it exits
                    model = command[-1]["model"]
                    if run_kwargs and hasattr(model, "run"):
                        # call first command using collected arguments only
                        if index == 0:
                            ret = model.run(**run_kwargs)
                        # pipe results through subsequent commands
                        else:
                            ret = model.run(ret, **run_kwargs)
                    # check if model has subshell
                    elif (
                        hasattr(model, "PicleConfig")
                        and getattr(model.PicleConfig, "subshell", None) is True
                    ):
                        # collect parent shells
                        for item in command[:-1]:
                            m = item["model"]
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
                    elif command[-1]["fields"]:
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
                                    ret = getattr(model, method_name)(**run_kwargs)
                                # pipe results through subsequent commands
                                else:
                                    ret = getattr(model, method_name)(ret, **run_kwargs)
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
                                    ret = getattr(model, method_name)(**run_kwargs)
                                # pipe results through subsequent commands
                                else:
                                    ret = getattr(model, method_name)(ret, **run_kwargs)
                            else:
                                self.write(
                                    f"Model '{model.__name__}' has no '{method_name}' "
                                    f"method defined for '{last_field_name}' function"
                                )
                        else:
                            self.write(
                                f"Model '{model.__name__}' has no 'run' method defined"
                            )
                        # run result through processors if any
                        for processor in json_schema_extra.get("processors", []):
                            ret = processor(ret)
                    else:
                        self.write(f"Incorrect command")
                        continue

        # returning True will close the shell
        if ret is True:
            return True
        elif ret:
            self.write(ret)
        return None
