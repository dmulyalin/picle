# Input Parsing

PICLE does more than split on spaces.

`App.parse_command()` has special handling for quoted strings, JSON-like chunks, JSON fields, and scalar conversion.

## Example Models

```python
from typing import Any, List, Union
from pydantic import BaseModel, Field, Json, StrictInt, StrictStr


class RunCommand(BaseModel):
    command: StrictStr = Field(None, description="Command text")

    @staticmethod
    def run(**kwargs):
        return kwargs


class PayloadCommand(BaseModel):
    data: Json[Any] = Field(None, description="JSON payload")
    label: Any = Field(None, description="Label")

    @staticmethod
    def run(**kwargs):
        return kwargs


class LimitsCommand(BaseModel):
    retries: StrictInt = Field(None, description="Retry count")
    name: StrictStr = Field(None, description="Job name")
    threshold: Any = Field(None, description="Threshold")

    @staticmethod
    def run(**kwargs):
        return kwargs


class BatchCommand(BaseModel):
    items: Union[StrictStr, List[StrictStr]] = Field(
        None, description="Collect multiple items"
    )
    tag: StrictStr = Field(None, description="Batch tag")

    @staticmethod
    def run(**kwargs):
        return kwargs


class Root(BaseModel):
    run_command: RunCommand = Field(None, alias="run-command")
    payload: PayloadCommand = Field(None)
    limits: LimitsCommand = Field(None)
    batch: BatchCommand = Field(None)
```

## Quoted Values

Single quotes and double quotes let you pass multi-word values as a single field value.

```text
picle#run-command command 'show version | match "Juniper: "'
{'command': 'show version | match "Juniper: "'}
```

```text
picle#run-command command "hello world"
{'command': 'hello world'}
```

Double-quoted single-word values work too:

```text
picle#run-command command "hello"
{'command': 'hello'}
```

## JSON-like Chunks

If a value starts with `{` or `[`, PICLE keeps collecting tokens until it sees a token that ends with the matching closing bracket.

That makes it possible to pass JSON-like text through the shell.

```text
picle#payload data [1, 2, 3] label demo
{'data': '[1, 2, 3]', 'label': 'demo'}
```

```text
picle#payload data {"person":{"name":"John","age":30}} label demo
{'data': '{"person":{"name":"John","age":30}}', 'label': 'demo'}
```

## `Json[...]` Fields Preserve Raw Input

`Json[...]` fields are special-cased in the parser.

PICLE keeps the raw text instead of converting values like `true`, `false`, or `null` before Pydantic sees them.

```text
picle#payload data true label demo
{'data': 'true', 'label': 'demo'}

picle#payload data false label demo
{'data': 'false', 'label': 'demo'}

picle#payload data null label demo
{'data': 'null', 'label': 'demo'}
```

## Automatic Scalar Conversion

For non-`str` fields, PICLE tries a lightweight conversion pass before validation.

- `True`, `False`, and `None` become Python values.
- Digit-only values become `int`.
- Values containing `.` are tried as `float`.

```text
picle#limits retries 3 threshold 3.14 name nightly
{'retries': 3, 'threshold': 3.14, 'name': 'nightly'}
```

String fields keep their string representation:

```text
picle#limits name 123
{'name': '123'}
```

## Repeating A Field

If your field accepts list-like input, you can repeat the field name to collect multiple values.

```text
picle#batch items val1 items val2 items val3 tag nightly
{'items': ['val1', 'val2', 'val3'], 'tag': 'nightly'}
```

Use this pattern when you want explicit, readable shell grammar for list input.