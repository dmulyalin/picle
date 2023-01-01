"""
This file contains Pydantic models to test PICLE 
by building sample App.
"""
from picle import App
from enum import Enum
from typing import List, Union, Optional
from pydantic import ValidationError, BaseModel, StrictStr, Field, StrictBool
from pydantic.main import ModelMetaclass
from pydantic.fields import ModelField

class NrCliPlugins(str, Enum):
    netmiko = 'netmiko'
    napalm = 'napalm'
    pyats = 'pyats'
    scrapli = 'scrapli'

class NrCfgPlugins(str, Enum):
    netmiko = 'netmiko'
    napalm = 'napalm'
    pyats = 'pyats'
    scrapli = 'scrapli'
    
class filters(BaseModel):
    FB: StrictStr = Field(None, description="Filter hosts using Glob Pattern")
    FL: List[StrictStr] = Field(None, description="Filter hosts using list of hosts' names")

class model_nr_cli(filters):
    commands: Optional[Union[StrictStr, List[StrictStr]]] = Field(None, description="CLI commands to send to devices")
    plugin: NrCliPlugins = Field("netmiko", description="Connection plugin name")
        
    @staticmethod
    def run(target="*", tgt_type="glob", **kwargs):
        print(f"Called salt nr cli, target: {target}, tgt_type: {tgt_type}, kwargs: {kwargs}")
    
class model_nr_cfg(filters):
    commands: Optional[Union[StrictStr, List[StrictStr]]] = Field(None, description="Configuration commands send to devices")
    plugin: NrCfgPlugins = Field("netmiko", description="Connection plugin name")

    @staticmethod
    def run(target="*", tgt_type="glob", **kwargs):
        print(f"Called salt nr cfg, target: {target}, tgt_type: {tgt_type}, kwargs: {kwargs}")
        
class model_nr(BaseModel):
    cli: model_nr_cli = Field(None, description="Send CLI commands to device")
    cfg: model_nr_cfg = Field(None, description="Send confguration to device")
    
    class PicleConfig:
        subshell = True
        prompt = "salt[nr]#"
    
class model_salt(BaseModel):
    target: StrictStr = Field("proxy:proxytype:nornir", description="SaltStack minions target value", title="target", required=False)
    tgt_type: StrictStr = Field("pillar", description="SaltStack minions targeting type", title="tgt_type", required=False)
    nr: model_nr = Field(None, description="Nornir Execution Module", title="nr", required=False)
    
    class PicleConfig:
        subshell = True
        prompt = "salt#"
    
class Root(BaseModel):
    salt: model_salt = Field(None, description="SaltStack Execution Modules")
    
    class PicleConfig:
        prompt = "picle#"
        ruler = ""
        intro = "PICLE Sample app"
        newline = "\r\n"
        completekey = "tab"
        
if __name__ == "__main__":
    shell = App(Root)
    shell.start()
