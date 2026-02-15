# PICLE API reference

This page describes the configuration hooks PICLE reads from your Pydantic models and fields.
It focuses on the parts you use when defining a shell (config, field metadata, execution, and output).
For full API docs of `App` and built-in models, keep reading to the mkdocstrings reference at the bottom.

## `PicleConfig` (model-level)

Any Pydantic model may define an inner `PicleConfig` class. PICLE reads attributes from it (when present).
Only a few are required; most are optional quality-of-life switches.

`PicleConfig` is intentionally “open-ended”: the core `App` reads a known set of attributes (documented below),
and specific built-in models may honor additional `PicleConfig` keys (for example, `ConfigModel`).

| Name | Meaning |
| --- | --- |
| `ruler` | Separator line char used by `cmd` help formatting (empty disables) |
| `intro` | Banner printed on shell start |
| `prompt` | Prompt string |
| `use_rich` | If `True` and Rich is installed, print via Rich console |
| `newline` | Output newline, default `\r\n` |
| `completekey` | Readline completion key name, default `tab` |
| `pipe` | Enables `|` and selects the pipe model (`"self"`, import string, or model class) |
| `processors` | List of callables applied to the first command result |
| `outputter` | Callable used to render output when not overridden |
| `outputter_kwargs` | Extra kwargs passed into `outputter` |

Common additional flags used by the core shell logic:

| Name | Meaning |
| --- | --- |
| `subshell` | If `True`, navigating to this model with no args enters a subshell (prompt changes, model is pushed onto a stack) |
| `methods_override` | Dict of `{app_method_name: model_method_name}` used to override `App` methods at runtime |

### Pipe configuration

If `pipe` is set, the `|` token becomes valid and starts a new “segment”. The next segment is parsed using the pipe model.
`pipe` can be:

```
"self"                  re-use the current model as the pipe model
"some.module.Model"     import a model by string
SomeModelClass          use a model class directly
```

Example (enable pipe functions and post-process the first command):

```python
from pydantic import BaseModel
from picle.models import PipeFunctionsModel, Outputters


class ShellModel(BaseModel):
    class PicleConfig:
        prompt = "picle#"
        intro = "PICLE Sample app"
        pipe = PipeFunctionsModel
        processors = [Outputters.outputter_json]
```

`processors` run on the first command segment only (before any `|` segments).

## `json_schema_extra` (field-level)

PICLE reads extra behavior from `Field(..., json_schema_extra={...})`.

Note: command tokens come from the field name (or its `alias` / `serialization_alias`), not from the Pydantic class name.

| Key | Meaning |
| --- | --- |
| `function` | Name of a model `@staticmethod` to call when `run()` is absent |
| `presence` | Constant value used when field is referenced without a value |
| `processors` | List of callables applied to the command result |
| `outputter` | Callable that formats output for this field (overrides model outputter) |
| `outputter_kwargs` | Extra kwargs passed into `outputter` |
| `multiline` | If `True`, the literal value `input` triggers multi-line collection |
| `root_model` | If `True`, pass the app root model as `root_model=...` |
| `picle_app` | If `True`, pass the `App` instance as `picle_app=...` |
| `use_parent_run` | If `True` (default), and the leaf model has no `run()`, PICLE searches parent models for a `run()` to execute. If `False`, the command errors unless the leaf model defines `run()` or `function`. |

### `function` vs `run()`

Execution is resolved like this:

1. If the current model has `run`, PICLE calls `model.run(**kwargs)`.
2. Otherwise, if the last referenced field sets `json_schema_extra={"function": "method_name"}`, PICLE calls `getattr(model, method_name)(**kwargs)`.

This lets small models define many “command -> staticmethod” fields, while larger models can centralize behavior in `run()`.

### Callable parameters (`run()` / field functions)

PICLE builds `**kwargs` from collected field values and calls either `run()` or the field-level `function`.
It can also inject extra context if (and only if) the callable declares a matching parameter name.

- `root_model`: injected when the leaf field sets `json_schema_extra={"root_model": True}`
- `picle_app`: injected when the leaf field sets `json_schema_extra={"picle_app": True}`
- `shell_command`: injected when the callable signature includes `shell_command`

`shell_command` is the parsed command context for the current segment: a list of model dicts produced by `parse_command()`.
This is useful when your function needs to inspect the command path, model defaults, or other parsing details.

#### Pipes: positional input + kwargs

When the command contains pipes (`|`), execution happens left-to-right by segment:

- Segment 0: `run_function(**kwargs)`
- Segment N (after `|`): `run_function(previous_result, **kwargs)`

If the segment’s callable declares `shell_command`, PICLE passes it as a keyword argument for that segment.

### `presence`

`presence` is useful for boolean-ish flags where you want the value to be set just by mentioning the field.

```python
from pydantic import BaseModel, Field


class Root(BaseModel):
    verbose: bool = Field(
        False,
        description="Enable verbose mode",
        json_schema_extra={"presence": True},
    )

    @staticmethod
    def run(**kwargs):
        return kwargs
```

Example interaction:

```
picle#verbose
{'verbose': True}
```

### Processors

Processors are just functions that transform results. They run in order.

```python
from typing import Any
from pydantic import BaseModel, Field
from picle.models import Outputters


class ModelShow(BaseModel):
    data_pprint: Any = Field(
        None,
        description="Show structured data using pprint",
        json_schema_extra={
            "function": "produce_structured_data",
            "processors": [Outputters.outputter_pprint],
        },
    )

    @staticmethod
    def produce_structured_data():
        return {"some": {"nested": {"data": None}}}
```

If you also set `PicleConfig.processors`, they run for the first segment after field-level processors.

### Multi-line input

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

## Result-specific outputters

Sometimes a single model-level outputter is not enough. If you need to choose an outputter based on runtime data,
return a tuple from `run()`:

```
(result, outputter)
(result, outputter, outputter_kwargs)
```

This overrides model and field outputters for that specific execution.

## `ConfigModel` (configuration shells)

PICLE ships a helper base model for “configuration-mode” shells: `picle.models.ConfigModel`.
It implements a common workflow:

- Load configuration from YAML (optional dependency: `pyyaml`)
- Stage edits into a temporary file (`<config_file>.tmp`)
- Review staged changes (`show changes`) and commit them (`commit`)
- Keep rotating backups on commit (`.old1`, `.old2`, ...)
- Roll back by loading a backup into the temp file (`rollback <n>`) and then committing

### `ConfigModel.PicleConfig` keys

`ConfigModel` reads additional settings from the concrete model’s `PicleConfig`.
These keys are **only honored by `ConfigModel`** (the core `App` ignores them):

| Name | Meaning |
| --- | --- |
| `config_file` | Path to the YAML config file (default: `configuration.yaml`) |
| `backup_on_save` | How many `.oldN` backups to keep when committing (0 disables backups) |
| `commit_hook` | Optional callable invoked after a successful commit |

### Typical command flow

Assuming you mount a `ConfigModel`-derived model under `configure_terminal`:

```
picle#configure_terminal
... (optionally enters a subshell if `PicleConfig.subshell = True`)

...#logging terminal severity debug
Configuration updated (uncommitted). Use 'commit' to save or 'show changes' to review.

...#show changes
--- app_config.yaml
+++ app_config.yaml.tmp
...

...#commit
Configuration committed successfully
```

## Mounting/removing models at runtime

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

## PICLE App

::: picle.App

## PICLE Build In Models

::: picle.models.Filters
::: picle.models.Outputters
::: picle.models.PipeFunctionsModel
::: picle.models.MAN
