# Processors

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