# PICLE

PICLE builds interactive command-line shells from Pydantic v2 models.
It uses Python’s standard `cmd` loop under the hood and turns each entered line
into a walk through a model tree:

```
Root model
  ├─ field -> sub-model (becomes a command group)
  ├─ field -> value (collects validated input)
  └─ field -> function (execute when ENTER is pressed)
```

What you get out of the box:

- Nested commands (models inside models)
- Validation and type conversion via Pydantic
- Inline discovery with `?` / `??` and tab completion
- Optional piping with `|` to post-process results
- Optional Rich/Tabulate/YAML output helpers (extras)

Install:

```
pip install picle
```

A minimal example:

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
		intro = "PICLE sample app"
		prompt = "picle#"


if __name__ == "__main__":
	App(Root).start()
```
