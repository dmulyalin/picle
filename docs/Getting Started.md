# Getting Started

## Introducing PICLE

Command-line interfaces are great when you want a fast workflow: type a command, get output, repeat.
In practice, a good interactive shell also needs help, completion, and input validation.

PICLE provides those features by turning Pydantic v2 models into an interactive shell.
You define a model tree, and PICLE interprets the command line as a walk through that tree.

At a high level, your shell looks like this:

```
Root
  ├─ command -> SubModel
  │    ├─ arg -> Field (collect value)
  │    ├─ flag -> Field (presence)
  │    └─ <ENTER> -> run() / field function
  └─ command -> Field (collect value)
```

Concretely: field names (or `alias` / `serialization_alias`) become command tokens.
Tokens after a leaf field become that field’s value(s). Once PICLE has enough information, 
it validates the collected data with Pydantic and then executes your code.

How a line is processed:

```
user input
  -> parse tokens into (models + fields)
  -> collect values (supports quotes, JSON-ish {..} / [..], multiline)
  -> validate with Pydantic
  -> execute (model.run or field function)
  -> processors / outputter
  -> print
```

## A small shell

This creates:

```
Root
  └─ show
    ├─ version   (function)
    └─ clock     (function)
```

```python
import time
from typing import Any

from pydantic import BaseModel, Field
from picle import App


class Show(BaseModel):
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
  show: Show = Field(None, description="Show commands")

  class PicleConfig:
    prompt = "picle#"
    intro = "PICLE Sample app"


if __name__ == "__main__":
  App(Root).start()
```

Try it:

```
picle#show version
0.1.0
picle#show clock
Fri May  2 22:44:01 2025
```

## What gets executed

PICLE decides what to call in this order:

1) If the current model has a `run(**kwargs)` method, it calls `run`.
2) Otherwise, if the last referenced field has `json_schema_extra={"function": "..."}`, PICLE calls that model staticmethod.

That keeps simple “command -> function” shells small, while still supporting bigger models that centralize behavior in `run()`.

## Help and discovery

PICLE’s help is model-driven:

```
picle#?
... shows available top-level commands and built-in commands

picle#show ?
... shows available fields under "show"

picle#show version ?
... shows what ENTER will do
```

For a command tree view:

```
picle#man tree
```

For a JSON schema (useful if you want to expose your shell as documented data):

```
picle#man json-schema
```

## Subshells (optional)

If a model sets `PicleConfig.subshell = True`, you can “enter” that model as a subshell.
When you navigate to the model without providing arguments, PICLE pushes it onto a shell stack and updates the prompt.

Shell navigation commands:

```
exit   leave current subshell
top    return to the root shell
end    exit the app
pwd    print current shell path
cls    clear the screen
```

## Pipes (optional)

If the current model declares `PicleConfig.pipe`, the `|` token starts a new command segment.
The second segment receives the previous segment’s result as its first argument.

```
segment 0 (produce data)
  | segment 1 (transform/format)
  | segment 2 (transform/format)
```

PICLE includes a ready-to-use pipe model (`PipeFunctionsModel`) with filters and outputters.

## Configuration shells with `ConfigModel`

If you want a CLI that edits a structured YAML configuration, PICLE includes `picle.models.ConfigModel`.
It lets users navigate a nested Pydantic model, stage edits into `<config_file>.tmp`, review diffs, and then commit.

Minimal shape:

```python
from pydantic import BaseModel, Field
from picle import App
from picle.models import ConfigModel, PipeFunctionsModel


class Logging(BaseModel):
  severity: str = Field(None, description="Log severity")


class MyConfig(ConfigModel):
  logging: Logging = Field(None, description="Logging config")

  class PicleConfig:
    subshell = True
    prompt = "app[cfg]#"
    config_file = "app_config.yaml"


class Root(BaseModel):
  configure: MyConfig = Field(None, description="Edit configuration")

  class PicleConfig:
    prompt = "app#"
    pipe = PipeFunctionsModel


if __name__ == "__main__":
  App(Root).start()
```

Example interaction:

```
app#configure
app[cfg]#logging severity debug
Configuration updated (uncommitted). Use 'commit' to save or 'show changes' to review.

app[cfg]#show changes
... unified diff ...

app[cfg]#commit
Configuration committed successfully
```

`ConfigModel` also honors a additional `PicleConfig` parameters:

- `config_file`: YAML config path (default: `configuration.yaml`)
- `backup_on_save`: number of rotating backups to keep on commit (default: 5)
- `commit_hook`: optional callable executed after a successful commit

Notes:

- `show configuration` prints the running config, `show changes` prints the staged diff.
- `clear-changes` discards the staged temp file; `erase-configuration` stages an empty config.
- `rollback <n>` loads `app_config.yaml.old<n>` into the temp file for review/commit.

## Multi-line input

If a field sets `json_schema_extra={"multiline": True}`, the user can type `input` as the value to start multi-line collection.
PICLE reads lines until EOF (Ctrl+D), then joins them with newlines and validates the result.

## Sample shell apps

If you want copy/paste starting points, the repository includes a couple of small runnable examples:

- `test/docs_sample_app_1.py`: a tiny “show version/clock” shell
- `test/config_app_example.py`: a complete `ConfigModel` configuration shell example