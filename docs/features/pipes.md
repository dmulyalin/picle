# Pipes

If PicleConfig class `pipe` is set, the `|` token becomes valid and starts a new “segment”. The next segment is parsed using the pipe model.
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


!!! note `processors` run on the first command segment only (before any `|` segments). They do not apply to subsequent pipe segments. If you want to post-process the output of a pipe segment, use an outputter or a pipe function in that segment.