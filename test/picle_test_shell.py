"""
This file contains Pydantic models to test PICLE
by building sample App.
"""

import json
from picle import App
from picle.models import PipeFunctionsModel, Formatters, Outputters
from enum import Enum
from typing import List, Union, Optional, Callable, Any
from pydantic import (
    ValidationError,
    BaseModel,
    StrictStr,
    Field,
    StrictBool,
    Json,
    ConfigDict,
)


class NrCliPlugins(str, Enum):
    netmiko = "netmiko"
    napalm = "napalm"
    pyats = "pyats"
    scrapli = "scrapli"


class NrCfgPlugins(str, Enum):
    netmiko = "netmiko"
    napalm = "napalm"
    pyats = "pyats"
    scrapli = "scrapli"


class filters(BaseModel):
    FB: StrictStr = Field(
        None,
        description="Filter hosts using Glob Pattern",
        examples=["router*", "sw[123]"],
    )
    FL: Union[StrictStr, List[StrictStr]] = Field(
        None, description="Filter hosts using list of hosts' names", examples="sw1"
    )
    hosts: Union[StrictStr, List[StrictStr]] = Field(
        None, description="Select hostnames to run this task for"
    )

    @staticmethod
    def source_hosts():
        return ["ceos1", "ceos2", "ceos3"]


class NextModel(BaseModel):
    some: StrictStr = Field(None, description="some field")

    @staticmethod
    def run(**kwargs):
        return f"Called salt nr cli, kwargs: {kwargs}"


class EnumTableTypes(str, Enum):
    table_brief = "brief"
    table_terse = "terse"
    table_extend = "extend"


class model_nr_cli(filters):
    commands: Union[StrictStr, List[StrictStr]] = Field(
        ..., description="CLI commands to send to devices", required=True
    )
    plugin: NrCliPlugins = Field("netmiko", description="Connection plugin name")
    next_model: NextModel = Field(None, description="Next model handling test")
    add_details: StrictBool = Field(
        None, description="Show detailed output", json_schema_extra={"presence": True}
    )
    table: EnumTableTypes = Field(
        None,
        description="Table format (brief, terse, extend) or parameters or True",
        json_schema_extra={"presence": "brief"},
    )

    @staticmethod
    def run(**kwargs):
        return f"Called salt nr cli, kwargs: {kwargs}"

    class PicleConfig:
        subshell = True
        prompt = "salt[nr-cli]#"


class model_nr_cfg(filters):
    commands: Optional[Union[StrictStr, List[StrictStr]]] = Field(
        None, description="Configuration commands send to devices"
    )
    plugin: NrCfgPlugins = Field("netmiko", description="Connection plugin name")

    @staticmethod
    def run(**kwargs):
        return kwargs

    class PicleConfig:
        processors = [Formatters.formatter_json]


class model_nr(BaseModel):
    cli: model_nr_cli = Field(None, description="Send CLI commands to device")
    cfg: model_nr_cfg = Field(None, description="Send configuration to device")

    class PicleConfig:
        subshell = True
        prompt = "salt[nr]#"


class model_salt(BaseModel):
    target: StrictStr = Field(
        "proxy:proxytype:nornir",
        description="SaltStack minions target value",
        title="target",
    )
    tgt_type: StrictStr = Field(
        "pillar", description="SaltStack minions targeting type", title="tgt_type"
    )
    nr: model_nr = Field(None, description="Nornir Execution Module", title="nr")


class ShowXYZModel(BaseModel):
    status: StrictStr = Field("anystatus", description="XYZ status")

    @staticmethod
    def run(*args, **kwargs):
        if kwargs.get("status") == "anystatus":
            return [
                {"name": "name3", "status": "dead", "keepalive": "123"},
                {"name": "name1", "status": "alive", "keepalive": "123"},
                {"name": "name2", "status": "any", "keepalive": "123"},
            ]
        else:
            return None


class model_show(BaseModel):
    version: Callable = Field("show_version", description="Show software version")
    clock: Callable = Field("show_clock", description="Show current clock")
    joke: Callable = Field("show_joke", description="Show joke")
    data: Callable = Field(
        "produce_structured_data", description="Produce structured data"
    )
    data_pprint: Callable = Field(
        "produce_structured_data",
        description="Show data using pprint formatter",
        json_schema_extra={"processors": [Formatters.formatter_pprint]},
    )
    data_rich_json: Callable = Field(
        "produce_structured_data",
        description="Show data using rich_json outputter",
        json_schema_extra={"outputter": Outputters.outputter_rich_json},
    )
    data_rich_table: Callable = Field(
        "produce_structured_data_table",
        description="Show data using rich_table outputter",
        json_schema_extra={"outputter": Outputters.outputter_rich_table},
    )
    XYZ: ShowXYZModel = Field(None, description="Show XYZ status")

    class PicleConfig:
        pipe = PipeFunctionsModel

    @staticmethod
    def show_version():
        return "0.1.0"

    @staticmethod
    def show_clock():
        import time

        return time.ctime()

    @staticmethod
    def show_joke():
        return """
Why did the network engineer always carry a ladder?

Because he wanted to reach the highest levels of connectivity... and occasionally fix the "cloud" when it crashed!

The End.
        """

    @staticmethod
    def produce_structured_data():
        return {
            "some": {"dictionary": {"data": None}},
            "more": {"dictionary": ["data"]},
            "even": {"more": {"dictionary": "data"}},
        }

    @staticmethod
    def produce_structured_data_table():
        return [
            {"name": "name3", "key1": "key1_value3", "key2": "key2_value3"},
            {"name": "name1", "key1": "key1_value1", "key2": "key2_value1"},
            {"name": "name2", "key1": "key1_value2", "key2": "key2_value2"},
        ]


class model_PicleConfig_outputter_with_run_method(BaseModel):
    string_argument: StrictStr = Field(None, description="Input some string value")

    @staticmethod
    def run(**kwargs):
        return kwargs

    class PicleConfig:
        outputter = Outputters.outputter_rich_json


class model_outputter_rich_table_with_PicleConfig_kwargs(BaseModel):
    string_argument: StrictStr = Field(None, description="Input some string value")

    @staticmethod
    def run(**kwargs):
        return [
            {"name": "name3", "key1": "key1_value3", "key2": "key2_value3"},
            {"name": "name1", "key1": "key1_value1", "key2": "key2_value1"},
            {"name": "name2", "key1": "key1_value2", "key2": "key2_value2"},
        ]

    class PicleConfig:
        outputter = Outputters.outputter_rich_table
        outputter_kwargs = {"sortby": "name"}


class model_PicleConfig_outputter_with_callable(BaseModel):
    argument: Callable = Field("some_function", description="Execute command")

    @staticmethod
    def some_function():
        return {"some": "data"}

    class PicleConfig:
        processors = [Formatters.formatter_json]
        outputter = Outputters.outputter_rich_print


class model_TestJsonInput(BaseModel):
    data: Json[Any] = Field(None, description="JSON Data string")
    arg: Any = Field(None, description="some field")
    arg1: Any = Field(None, description="some field")

    @staticmethod
    def run(**kwargs):
        return kwargs


class model_TestMultilineInput(BaseModel):
    data: StrictStr = Field(
        None, description="Multi line string", json_schema_extra={"multiline": True}
    )
    arg: Any = Field(None, description="some field")

    @staticmethod
    def run(**kwargs):
        return kwargs


class model_TestResultSpecificOutputter(BaseModel):
    data: StrictStr = Field(None, description="string")
    arg: Any = Field(None, description="some field")

    @staticmethod
    def run(**kwargs):
        return kwargs, Outputters.outputter_rich_print, {}


class model_TestResultSpecificOutputterNoKwargs(BaseModel):
    data: StrictStr = Field(None, description="string")
    arg: Any = Field(None, description="some field")

    @staticmethod
    def run(**kwargs):
        return kwargs, Outputters.outputter_rich_print


class model_TestCommandValues(BaseModel):
    command: StrictStr = Field(None, description="string")

    @staticmethod
    def run(**kwargs):
        return kwargs


class model_model_TestAliasHandlingNestedModel(BaseModel):
    command_no_alias: StrictStr = Field(None, description="string")
    command_with_alias: StrictStr = Field(
        None, description="string", alias="enter-command"
    )

    @staticmethod
    def run(**kwargs):
        return kwargs


class model_model_TestAliasHandlingMandatoryField(BaseModel):
    mandatory_field_with_alias: StrictStr = Field(
        ...,
        description="string",
        required=True,
        serialization_alias="mandatory-field-with-alias",
    )

    @staticmethod
    def run(**kwargs):
        return kwargs


class model_TestAliasHandling(BaseModel):
    foo_bar_command: StrictStr = Field(
        None, description="string", alias="foo-bar-command"
    )
    nested_command: model_model_TestAliasHandlingNestedModel = Field(
        None,
        description="Enter command",
    )
    mandatory_field_test: model_model_TestAliasHandlingMandatoryField = Field(
        None, description="Mandatry field"
    )

    @staticmethod
    def run(**kwargs):
        return kwargs


class test_mount_model(BaseModel):
    param: StrictStr = Field(None, description="string")

    @staticmethod
    def run(**kwargs):
        return kwargs


class model_MountTesting(BaseModel):
    """
    Test handling models mounting at a runtime from within model calls
    """

    mount_add: StrictStr = Field(
        None,
        description="Mount point name to add",
        json_schema_extra={"picle_app": True, "function": "mount_add_method"},
    )
    mount_remove: StrictStr = Field(
        None,
        description="Mount point name to remove",
        json_schema_extra={"picle_app": True, "function": "mount_remove_method"},
    )

    @staticmethod
    def mount_add_method(picle_app, mount_add):
        picle_app.model_mount(test_mount_model, mount_add)

    @staticmethod
    def mount_remove_method(picle_app, mount_remove):
        picle_app.model_remove(mount_remove)


class EnumTaskTypes(str, Enum):
    cli = "cli"
    cfg = "cfg"


class model_EnumFieldWithSameName(BaseModel):
    task: EnumTaskTypes = Field(None, description="Enum field")
    client: StrictStr = Field(None, description="String field")

    @staticmethod
    def run(**kwargs):
        return kwargs


class Root(BaseModel):
    salt: model_salt = Field(None, description="SaltStack Execution Modules")
    show: model_show = Field(None, description="Show commands")
    test_PicleConfig_outputter_with_run_method: (
        model_PicleConfig_outputter_with_run_method
    ) = Field(None, description="Command to test PicleConfig outputter with run method")
    test_PicleConfig_outputter_with_callable: (
        model_PicleConfig_outputter_with_callable
    ) = Field(None, description="Command to test PicleConfig outputter with callable")
    test_outputter_rich_table_with_PicleConfig_kwargs: (
        model_outputter_rich_table_with_PicleConfig_kwargs
    ) = Field(None, description="Command to test PicleConfig outputter with callable")
    test_json_input: model_TestJsonInput = Field(None, description="Test JSON input")
    test_multiline_input: model_TestMultilineInput = Field(
        None, description="Test Multiline input"
    )
    test_result_specific_outputter: model_TestResultSpecificOutputter = Field(
        None,
        description="Command to test result specific outputter with outputter kwargs",
    )
    test_result_specific_outputter_no_kwargs: (
        model_TestResultSpecificOutputterNoKwargs
    ) = Field(
        None,
        description="Command to test result specific outputter with outputter without kwargs",
    )
    test_command_values: model_TestCommandValues = Field(
        None,
        description="Enter command",
    )
    test_alias_handling: model_TestAliasHandling = Field(
        None,
        description="Enter command",
    )
    test_alias_handling_top: StrictStr = Field(
        None, description="Should se dashes", alias="test-alias-handling-top"
    )
    test_mount_model: model_MountTesting = Field(None, description="Mount testing")
    test_enum_and_field_with_same_name: model_EnumFieldWithSameName = Field(
        None, description="Enum and field with same name"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @staticmethod
    def run(**kwargs):
        return kwargs

    class PicleConfig:
        prompt = "picle#"
        ruler = ""
        intro = "PICLE Sample app"
        newline = "\r\n"
        completekey = "tab"


if __name__ == "__main__":
    shell = App(Root)
    shell.start()
