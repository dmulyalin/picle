import time
from picle import App
from typing import Any
from pydantic import BaseModel, Field


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

    @staticmethod
    def show_version():
        return "0.1.0"

    @staticmethod
    def show_clock():
        return time.ctime()


class Root(BaseModel):
    show: model_show = Field(None, description="Show commands")

    class PicleConfig:
        prompt = "picle#"
        intro = "PICLE Sample app"


if __name__ == "__main__":
    shell = App(Root)
    shell.start()
