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
# from pydantic.main import ModelMetaclass
# from pydantic.fields import ModelField


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
    
    def __init__(self, root):
        self.root = root
        self.shell = self.root.construct()
        self.shells = [self.shell]
        
        # extract comnfig from shell model
        if hasattr(self.shell, "PicleConfig"):
            self.ruler = getattr(self.shell.PicleConfig, "ruler", self.ruler)
            self.intro = getattr(self.shell.PicleConfig, "intro", self.intro)
            self.prompt = getattr(self.shell.PicleConfig, "prompt", self.prompt)
            self.newline = getattr(self.shell.PicleConfig, "newline", self.newline)
            self.completekey = getattr(self.shell.PicleConfig, "completekey", self.completekey)
        
        # mount override methods
        if getattr(self.shell.PicleConfig, "methods_override"):
            for mount, override in self.shell.PicleConfig.methods_override.items():
                setattr(self, mount, getattr(self.shell, override))
            
        super(App, self).__init__()

    def start(self) -> None:
        self.cmdloop()

    def emptyline(self) -> None:
        """Override empty line method to not run last command"""
        return None
        
    def _save_collected_value(self, field: dict, value: str) -> None:
        """
        Helper function to save collected value into field values

        :param field: field dictionary
        :param value: value to save string
        """
        # attempt to mutate value
        if value.title() == "False":  # convert value to boolean
            value = False
        elif value.title() == "True":
            value = True
        elif value.title() == "None":
            value = None
        elif value.isdigit():  # convert to integer
            value = int(value)
        elif "." in value:  # convert to float
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

    def parse_command(self, command: str, validate: bool = False) -> list:
        """
        Function to parse command string and construct
        a list of model references and fields values.

        :param command: command string
        """
        current_model = {"model": self.shell, "fields": [], "parameter": ...}
        current_field = {}
        models = [current_model]
        parameters = [i for i in command.split(" ") if i.strip()]

        # iterate over command parameters and decide if its a reference
        # to a model or model's field value
        while parameters:
            parameter = parameters.pop(0)
            # collect single quoted field value
            if '"' in parameter and current_field:
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
            elif current_model["model"].model_fields.get(parameter):
                field = current_model["model"].model_fields[parameter]
                # handle next level model reference
                if isinstance(field.annotation, ModelMetaclass):
                    current_model = {
                        "model": field.annotation,
                        "fields": [],
                        "parameter": parameter,
                    }
                    models.append(current_model)
                    current_field = {}  # empty current field
                # handle field value
                elif isinstance(field, FieldInfo):
                    current_field = {"name": parameter, "values": ...}
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
        # validated collected values
        if validate:
            self._validate_values(models)

        return models

    def print_model_help(self, model: dict, verbose: bool = False, match: str = None) -> None:
        """
        Function to form and print help message for model fields.
        
        :param match: only collect help for fields that start with ``match`` string
        """
        last_field = model["fields"][-1] if model["fields"] else None
        lines = {}  # dict of {cmd: cmd_help}
        width = 0  # record longest command width for padding
        # print help message only for last collected field
        if last_field and last_field["values"] == ...:
            field = model["model"].model_fields[last_field["name"]]
            name = f"<{last_field['name']} value>"
            # add options for enumerations
            if isinstance(field.annotation, enum.EnumMeta):
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
                        f"; default '{field.get_default()}', type '{field._type_display()}', "
                        f"required {field.required}"
                    )
            width = max(width, len(name))
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
                # filter fields
                if match and not name.startswith(match):
                    continue
                lines[name] = f"{field.description}"
                if verbose:
                    lines[name] += (
                        f"; default '{field.get_default()}', type '{field._type_display()}', "
                        f"required {field.required}"
                    )
                width = max(width, len(name))
        # form help lines
        help_msg = []
        for k in sorted(lines.keys()):
            padding = " " * (width - len(k)) + (" " * 4)
            help_msg.append(f"{k}{padding}{lines[k]}")
        # print help message
        print(self.newline.join(help_msg))

    def completedefault(self, text, line, begidx, endidx):
        """
        This method called for every  command parameter on
        complete key hit except for the very first one.
        """
        fieldnames = []
        try:
            command_models = self.parse_command(line)
            last_model = command_models[-1]["model"]
            # check if last model has fields collected
            if command_models[-1]["fields"]:
                last_field_name = command_models[-1]["fields"][-1]["name"]
                last_field = last_model.model_fields[last_field_name]
                last_field_value = command_models[-1]["fields"][-1]["values"]
                if isinstance(last_field_value, list):
                    last_field_value = last_field_value[-1]
                elif last_field_value == ...:
                    last_field_value = ""
                # check if need to exctract enum values
                if isinstance(last_field.annotation, enum.EnumMeta):
                    fieldnames = [
                        i.value
                        for i in last_field.annotation
                        if i.value.startswith(last_field_value)
                    ]
                # check if model has method to source field choices
                elif hasattr(last_model, f"source_{last_field_name}"):
                    fieldnames = getattr(last_model, f"source_{last_field_name}")()
                    fieldnames = [i for i in fieldnames if i.startswith(last_field_value)]
            # return a list of all model fields
            else:
                fieldnames = list(last_model.model_fields)
        except FieldLooseMatchOnly as e:
            model, parameter = e.args
            fieldnames = [
                f.name
                for f in model["model"].model_fields.values()
                # skip fields with already collected values from complete prompt
                if f.name.startswith(parameter)
                and not any(
                    True
                    for collected_field in model["fields"]
                    if collected_field["name"] == f.name
                    and collected_field["values"] is not ...
                )
            ]
        except FieldKeyError:
            pass
        except:
            tb = traceback.format_exc()
            print(tb)
            
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
            fieldnames.extend(command_models[-1]["model"].model_fields)
        # collect arguments that startswith last parameter
        except FieldLooseMatchOnly as e:
            model, parameter = e.args
            for f in model["model"].model_fields.values():
                if f.name.startswith(parameter):
                    fieldnames.append(f.name)
        # raised if no model fields matched last parameter
        except FieldKeyError as e:
            pass
        return sorted(fieldnames)

    def do_help(self, arg):
        """Print help message"""
        command_models = self.parse_command(arg.strip("?"))
        self.print_model_help(
            command_models[-1], verbose=True if arg.strip().endswith("?") else False
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
                print(self.newline.join(help_msg))

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
        print("->".join(path))

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
                    model,
                    verbose=True if line.strip().endswith("??") else False,
                    match=parameter
                )          
            except FieldKeyError as e:
                model, parameter = e.args
                model_name = (
                    model["model"].__name__
                    if hasattr(model["model"], "__name__")
                    else model["model"].__repr_name__()
                )
                print(
                    f"Incorrect command, '{parameter}' not part of '{model_name}' model fields"
                )                
            else:
                self.print_model_help(
                    command_models[-1],
                    verbose=True if line.strip().endswith("??") else False,
                )
        else:
            try:
                command_models = self.parse_command(line, validate=True)
            except FieldLooseMatchOnly as e:
                model, parameter = e.args
                # filter fields to return message for
                fields = [
                    f.name
                    for f in model["model"].model_fields.values()
                    if f.name.startswith(parameter)
                ]
                print(
                    f"Incomplete command, possible completions: " f"{', '.join(fields)}"
                )
            except FieldKeyError as e:
                model, parameter = e.args
                model_name = (
                    model["model"].__name__
                    if hasattr(model["model"], "__name__")
                    else model["model"].__repr_name__()
                )
                print(
                    f"Incorrect command, '{parameter}' not part of '{model_name}' model fields"
                )
            except ValidationError as e:
                print(e)
            else:
                # collect arguments
                run_kwargs = {
                    f["name"]: f["values"]
                    for model in command_models
                    for f in model["fields"]
                    if f["values"] is not ...
                }
                # run model "run" function if it exits
                model = command_models[-1]["model"]
                if hasattr(model, "run"):
                    ret = model.run(**run_kwargs)
                # check if model has subshell
                elif (
                    hasattr(model, "PicleConfig")
                    and getattr(model.PicleConfig, "subshell", None) is True
                ):
                    # collect parent shells
                    for item in command_models[:-1]:
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
                elif command_models[-1]["fields"]:
                    # check if last field refers to callable e.g. function
                    last_field_name = command_models[-1]["fields"][-1]["name"]
                    last_field = model.model_fields[last_field_name]
                    if last_field.annotation is Callable:
                        method_name = last_field.get_default()
                        if method_name and hasattr(model, method_name):
                            ret = getattr(model, method_name)(**run_kwargs)
                        else:
                            print(
                                f"Model '{model.__name__}' has no '{method_name}' "
                                f"method defined for '{last_field_name}' Callable field"
                            )
                    else:
                        print(f"Model '{model.__name__}' has no 'run' method defined")
                else:
                    print(f"Incorrect command")
        # returning True will close the shell
        if ret is True:
            return True
        elif ret:
            print(ret)
        return None
