# Fields Presence

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