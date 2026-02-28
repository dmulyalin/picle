# Mounting/removing models at runtime

`App` can add/remove models to the root tree:

```python
from pydantic import BaseModel, Field, StrictStr
from picle import App


class Mounted(BaseModel):
    param: StrictStr = Field(None, description="Param string")

    @staticmethod
    def run(**kwargs):
        return kwargs


class Root(BaseModel):
    command: StrictStr = Field(None, description="Some command")


shell = App(Root)
shell.model_mount(Mounted, ["another_command"])
shell.model_remove(["another_command"])
```

Notes:

- `path` may be a list of segments or a single string.
- `model_mount` can only mount under an existing path, except for the final segment (which is created).
- Mounted fields are added to the root model’s `model_fields` and participate in completion/help.