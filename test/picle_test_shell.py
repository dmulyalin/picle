"""
This file contains Pydantic models to test PICLE 
by building sample App.
"""
from picle import App
from picle.models import PipeFunctionsModel, Formatters
from enum import Enum
from typing import List, Union, Optional, Callable
from pydantic import ValidationError, BaseModel, StrictStr, Field, StrictBool


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
    FB: StrictStr = Field(None, description="Filter hosts using Glob Pattern")
    FL: Union[StrictStr, List[StrictStr]] = Field(
        None, description="Filter hosts using list of hosts' names"
    )
    hosts: Union[StrictStr, List[StrictStr]] = Field(
        None, description="Select hostnames to run this task for"
    )

    @staticmethod
    def source_hosts():
        return ["ceos1", "ceos2", "ceos3"]


class model_nr_cli(filters):
    commands: Union[StrictStr, List[StrictStr]] = Field(
        description="CLI commands to send to devices"
    )
    plugin: NrCliPlugins = Field("netmiko", description="Connection plugin name")
    add_details: StrictBool = Field(
        None, description="Show detailed output", json_schema_extra={"presence": True}
    )

    @staticmethod
    def run(**kwargs):
        return f"Called salt nr cli, kwargs: {kwargs}"


class model_nr_cfg(filters):
    commands: Optional[Union[StrictStr, List[StrictStr]]] = Field(
        None, description="Configuration commands send to devices"
    )
    plugin: NrCfgPlugins = Field("netmiko", description="Connection plugin name")

    @staticmethod
    def run(**kwargs):
        return f"Called salt nr cfg, kwargs: {kwargs}"


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

    class PicleConfig:
        subshell = True
        prompt = "salt#"


class model_show(BaseModel):
    version: Callable = Field("show_version", description="Show software version")
    clock: Callable = Field("show_clock", description="Show current clock")
    joke: Callable = Field("show_joke", description="Show joke")
    data: Callable = Field(
        "produce_structured_data", description="Produce structured data"
    )
    data_pprint: Callable = Field(
        "produce_structured_data",
        description="Show data using pprint outputter",
        json_schema_extra={"processors": [Formatters.formatter_pprint]},
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
        }


class Root(BaseModel):
    salt: model_salt = Field(None, description="SaltStack Execution Modules")
    show: model_show = Field(None, description="Show commands")

    class PicleConfig:
        prompt = "picle#"
        ruler = ""
        intro = "PICLE Sample app"
        newline = "\r\n"
        completekey = "tab"


if __name__ == "__main__":
    shell = App(Root)
    shell.start()
