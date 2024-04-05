from picle import App
from typing import Callable
from pydantic import BaseModel, Field


class model_show(BaseModel):
    version: Callable = Field("show_version", description="Show software version")
    clock: Callable = Field("show_clock", description="Show current clock")

    @staticmethod
    def show_version():
        return "0.1.0"

    @staticmethod
    def show_clock():
        import time

        return time.ctime()


class Root(BaseModel):
    show: model_show = Field(None, description="Show commands")

    class PicleConfig:
        prompt = "picle#"
        intro = "PICLE Sample app"


if __name__ == "__main__":
    shell = App(Root)
    shell.start()
