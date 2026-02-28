# Multi-line input

If a field enables multi-line input, the user can type the literal value `input` to start collection.
PICLE reads lines until EOF (Ctrl+D) and uses the collected text (joined by `\n`) as the field value.

```python
from typing import Any
from pydantic import BaseModel, Field, StrictStr


class TestMultilineInput(BaseModel):
    data: StrictStr = Field(
        None,
        description="Multi line string",
        json_schema_extra={"multiline": True},
    )
    arg: Any = Field(None, description="Some field")

    @staticmethod
    def run(**kwargs):
        return kwargs


class Root(BaseModel):
    test_multiline_input: TestMultilineInput = Field(
        None,
        description="Multi-line input demo",
    )
```

Help shows the `input` option when appropriate:

```
picle#test_multiline_input data ?
 <'data' value>    Multi line string
 input             Collect value using multi line input mode
```

Invoking multi-line collection:

```
picle#test_multiline_input data input arg foo
Enter lines and hit Ctrl+D to finish multi line input
line 1
line 2
<Ctrl+D>
```