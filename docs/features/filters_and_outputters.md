# Filters And Outputters

This page complements [Pipes](pipes.md).

`picle.models.PipeFunctionsModel` bundles ready-to-use filters and outputters that you can expose with `PicleConfig.pipe`.

The same outputter callables can also be attached directly to fields or to `PicleConfig.outputter`.

## Enabling Built-in Pipe Functions

```python
from typing import Any
from pydantic import BaseModel, Field, StrictStr
from picle.models import PipeFunctionsModel


class ShowCommands(BaseModel):
    joke: Any = Field(
        None,
        description="Show a joke",
        json_schema_extra={"function": "show_joke"},
    )
    data: Any = Field(
        None,
        description="Produce structured data",
        json_schema_extra={"function": "produce_data"},
    )
    inventory: Any = Field(
        None,
        description="Produce tabular data",
        json_schema_extra={"function": "produce_inventory"},
    )

    @staticmethod
    def show_joke():
        return """
Why did the network engineer always carry a ladder?

Because he wanted to reach the highest levels of connectivity.

The End.
        """

    @staticmethod
    def produce_data():
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
    def produce_inventory():
        return [
            {"name": "name3", "key1": "key1_value3", "key2": "key2_value3"},
            {"name": "name1", "key1": "key1_value1", "key2": "key2_value1"},
            {"name": "name2", "key1": "key1_value2", "key2": "key2_value2"},
        ]

    class PicleConfig:
        pipe = PipeFunctionsModel


class Notes(BaseModel):
    text: StrictStr = Field(None, description="Markdown or plain text")

    @staticmethod
    def run(**kwargs):
        return kwargs.get("text", "")

    class PicleConfig:
        pipe = PipeFunctionsModel
```

## Filters

`PipeFunctionsModel` includes three text filters.

- `include`: keep only lines that contain the requested pattern.
- `exclude`: drop lines that contain the requested pattern.
- `last`: keep only the last `N` lines.

```text
picle#show joke | include Why
Why did the network engineer always carry a ladder?
```

```text
picle#show joke | exclude Why
 ... the line containing `Why` is removed ...
```

```text
picle#show joke | last 1
The End.
```

Filters are chainable:

```text
picle#show joke | include d | exclude End
```

## Structured Outputters

The built-in outputters cover common CLI presentation needs.

- `pprint`: Python pretty-print formatting.
- `json`: JSON with configurable indentation and sorting.
- `yaml`: YAML output when `pyyaml` is installed.
- `nested`: recursive nested formatting, optionally with tabulated lists.
- `kv`: flatten nested data into `key.path: value` lines.
- `table`: text tables via `tabulate`.
- `rich-table`: Rich table rendering when Rich is installed.
- `markdown`: Rich Markdown rendering when Rich is installed.
- `save`: write output to a file.

```text
picle#show data | pprint
{'even': {'more': {'dictionary': 'data'}}, ...}
```

```text
picle#show data | json
{
    "even": {
        "more": {
            "dictionary": "data"
        }
    },
    ...
}
```

```text
picle#show data | yaml
even:
  more:
    dictionary: data
...
```

```text
picle#show data | kv
some.dictionary.data: None
more.dictionary.0: data
even.more.dictionary: data
list.0.more.dictionary: data
list.1.more.dictionary: data
```

`yaml` requires `pyyaml`. `table` requires `tabulate`. `rich-table` and `markdown` require `rich`.

## Table Output

The `table` outputter is a pipe model with its own fields.

```text
picle#show inventory | table
+----+--------+-------------+-------------+
|    | name   | key1        | key2        |
+====+========+=============+=============+
|  1 | name3  | key1_value3 | key2_value3 |
|  2 | name1  | key1_value1 | key2_value1 |
|  3 | name2  | key1_value2 | key2_value2 |
```

```text
picle#show inventory | table tablefmt plain
name    key1         key2
 1  name3   key1_value3  key2_value3
 2  name1   key1_value1  key2_value1
 3  name2   key1_value2  key2_value2
```

```text
picle#show inventory | table sortby name reverse
```

```text
picle#show inventory | table headers-exclude key2
```

## Markdown And Save

Any pipe-enabled command that returns text can be rendered as Markdown or saved to disk.

```text
picle#notes text "# Hello World" | markdown
```

```text
picle#notes text "hello" | save .\output.txt
```

`save` creates parent directories if needed, writes the data to the requested file, and still returns the original result.