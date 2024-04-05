# PICLE APIs Reference

## PicleConfig Class Reference

Each Pydantic model can have ``PicleConfig`` subclass defined
with model configuration parameters:

- ``ruler`` - The character used to draw separator lines under the help-message headers. If empty, no ruler line is drawn, defaults is empty
- ``intro`` - A string to issue as an intro or banner
- ``prompt`` - command line shell prompt
- ``newline`` - newline character to use while printing output, default is ``\r\n``
- ``completekey`` - is the ``readline`` name of a completion key, defaults to ``tab``
- ``pipe`` - reference to Pydantic model class to use with ``|`` (pipe) to process the 
	results with various functions, special value ``pipe = "self"`` instruct to use 
	current model for piping results through.

Sample ``PicleConfig`` definition:

```
class PipeFunctionsModel(BaseModel):
    """ define pip commands here """
	
class ShellModel(BaseModel):
    """ define command attributes here """
	
    class PicleConfig:
        prompt = "picle#"
        ruler = ""
        intro = "PICLE Sample app"
        newline = "\r\n"
        completekey = "tab"
		pipe = PipeFunctionsModel
```

## Model json_schema_extra reference

PICLE supports reading additional parameters for model ``json_schema_extra`` definition
to control its behavior. These ``json_schema_extra`` parameters supported:

- ``function`` - refers to ``@staticmethod`` of the model to call with command arguments
- ``presence`` - command argument set to ``presence`` value if command given
- ``processors`` - refers to a list of functions to use to process command execution results

### How to use processors

Processors allow to pass command execution results through a list of arbitrary functions.

In example below results returned by ``produce_structured_data`` passed through
pprint formatter function to produce pretty formatted string.

```
from picle.models import Formatters

class model_show(BaseModel):
    data_pprint: Callable = Field(
        "produce_structured_data", 
        description="Show data using pprint formatter", 
        json_schema_extra={
            "processors": [
                    Formatters.formatter_pprint
                ]
            }
    )

    @staticmethod        
    def produce_structured_data():
        return {"some": {"dictionary": {"data": None}}, "more": {"dictionary": ["data"]}, "even": {"more": {"dictionary": "data"}}}
```

## PICLE APP API

::: picle.App

## PICLE Build In Models

### PipeFunctionsModel

::: picle.models.PipeFunctionsModel
::: picle.models.Filters
::: picle.models.Formatters
