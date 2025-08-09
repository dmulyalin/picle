"""
This file contains Pydantic models to test PICLE
by building sample App.
"""

import json
from picle import App
from picle.models import PipeFunctionsModel, Outputters
from enum import Enum
from typing import List, Union, Optional, Any
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
        processors = [Outputters.outputter_json]


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
    version: Any = Field(
        None,
        description="Show software version",
        json_schema_extra={"function": "show_version"},
    )
    clock: Any = Field(
        None,
        description="Show current clock",
        json_schema_extra={"function": "show_clock"},
    )
    joke: Any = Field(
        None, description="Show joke", json_schema_extra={"function": "show_joke"}
    )
    data: Any = Field(
        None,
        description="Produce structured data",
        json_schema_extra={"function": "produce_structured_data"},
    )
    data_list: Any = Field(
        None,
        description="Produce structured data",
        json_schema_extra={"function": "produce_structured_data_list"},
    )
    data_pprint: Any = Field(
        None,
        description="Show data using pprint outputter",
        json_schema_extra={
            "processors": [Outputters.outputter_pprint],
            "function": "produce_structured_data",
        },
    )
    data_rich_json: Any = Field(
        None,
        description="Show data using rich_json outputter",
        json_schema_extra={
            "outputter": Outputters.outputter_json,
            "function": "produce_structured_data",
        },
    )
    data_rich_table: Any = Field(
        None,
        description="Show data using rich_table outputter",
        json_schema_extra={
            "outputter": Outputters.outputter_rich_table,
            "function": "produce_structured_data_table",
        },
    )
    XYZ: ShowXYZModel = Field(None, description="Show XYZ status")
    data_output_nested: Any = Field(
        None,
        description="Show data using nested outputter",
        json_schema_extra={
            "outputter": Outputters.outputter_nested,
            "function": "produce_structured_data",
        },
    )
    data_output_nested_tables: Any = Field(
        None,
        description="Show data using nested outputter with tables",
        json_schema_extra={
            "outputter": Outputters.outputter_nested,
            "outputter_kwargs": {"with_tables": True},
            "function": "produce_structured_data_nested_table",
        },
    )

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
            "list": [
                {"more": {"dictionary": "data"}},
                {"more": {"dictionary": "data"}},
            ],
        }

    @staticmethod
    def produce_structured_data_list():
        return [
            {"name": "name3", "key1": "key1_value3", "key2": "key2_value3"},
            {"name": "name1", "key1": "key1_value1", "key2": "key2_value1"},
            {"name": "name2", "key1": "key1_value2", "key2": "key2_value2"},
        ]

    @staticmethod
    def produce_structured_data_table():
        return [
            {"name": "name3", "key1": "key1_value3", "key2": "key2_value3"},
            {"name": "name1", "key1": "key1_value1", "key2": "key2_value1"},
            {"name": "name2", "key1": "key1_value2", "key2": "key2_value2"},
        ]

    @staticmethod
    def produce_structured_data_nested_table():
        return {
            "some": {"dictionary": {"data": None}},
            "more": {"dictionary": ["data"]},
            "even": {"more": {"dictionary": "data"}},
            "some_data": [
                {"name": "name3", "key1": "key1_value3", "key2": "key2_value3"},
                {"name": "name1", "key1": "key1_value1", "key2": "key2_value1"},
                {"name": "name2", "key1": "key1_value2", "key2": "key2_value2"},
            ],
            "some": {
                "more": {
                    "nested_data": [
                        {"name": "name3", "key1": "key1_value3", "key2": "key2_value3"},
                        {"name": "name1", "key1": "key1_value1", "key2": "key2_value1"},
                        {"name": "name2", "key1": "key1_value2", "key2": "key2_value2"},
                    ]
                }
            },
        }


class model_PicleConfig_outputter_with_run_method(BaseModel):
    string_argument: StrictStr = Field(None, description="Input some string value")

    @staticmethod
    def run(**kwargs):
        return kwargs

    class PicleConfig:
        outputter = Outputters.outputter_json


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


class model_PicleConfig_outputter_with_function(BaseModel):
    argument: Any = Field(
        None,
        description="Execute command",
        json_schema_extra={"function": "some_function"},
    )

    @staticmethod
    def some_function():
        return {"some": "data"}

    class PicleConfig:
        processors = [Outputters.json]


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
        return kwargs, Outputters.outputter_pprint, {}


class model_TestResultSpecificOutputterNoKwargs(BaseModel):
    data: StrictStr = Field(None, description="string")
    arg: Any = Field(None, description="some field")

    @staticmethod
    def run(**kwargs):
        return kwargs, Outputters.outputter_pprint


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


class model_TestSourceBoolen(BaseModel):
    value: Union[StrictBool, StrictStr, None] = Field(None, description="Value to test")

    @staticmethod
    def source_value():
        return [True, False, None, "foo", "bar"]

    @staticmethod
    def run(**kwargs):
        return kwargs


class TestEnumBoolen(Enum):
    true_value = True
    false_value = False
    foo = "foo"
    bar = "bar"


class model_TestEnumBoolen(BaseModel):
    value: TestEnumBoolen = Field(None, description="Value to test")

    @staticmethod
    def run(**kwargs):
        return kwargs


class Root(BaseModel):
    salt: model_salt = Field(None, description="SaltStack Execution Modules")
    show: model_show = Field(None, description="Show commands")
    test_PicleConfig_outputter_with_run_method: (
        model_PicleConfig_outputter_with_run_method
    ) = Field(None, description="Command to test PicleConfig outputter with run method")
    test_PicleConfig_outputter_with_function: (
        model_PicleConfig_outputter_with_function
    ) = Field(None, description="Command to test PicleConfig outputter with function")
    test_outputter_rich_table_with_PicleConfig_kwargs: (
        model_outputter_rich_table_with_PicleConfig_kwargs
    ) = Field(None, description="Command to test PicleConfig outputter")
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
    test_source_has_boolean_in_a_list: model_TestSourceBoolen = Field(
        None, description="Test sourcing boolean value"
    )
    test_enum_has_boolean_in_a_list: model_TestEnumBoolen = Field(
        None, description="Test sourcing boolean valuefrom enum"
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
        use_rich = False


if __name__ == "__main__":
    shell = App(Root)
    shell.start()
