# PICLE APIs Reference

## PicleConfig

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
- ``processors`` - list of functions to run results of `first command` through one by one
- ``outputter`` - function to output results, by default results written to stdout
- ``outputter_kwargs`` - dictionary containing any additional argument to use with outputter

Sample ``PicleConfig`` definition:

```
from picle.models import PipeFunctionsModel, Formatters, Outputters

class ShellModel(BaseModel):
    """ define command attributes here """
	<...>
	
    class PicleConfig:
        prompt = "picle#"
        ruler = ""
        intro = "PICLE Sample app"
        newline = "\r\n"
        completekey = "tab"
		pipe = PipeFunctionsModel
		processors = [Formatters.formatter_json]
		outputter = Outputters.outputter_rich_print 
		outputter_kwargs = {"any": "extra_argument"}
```

## Field json_schema_extra

PICLE supports reading additional parameters from model Field's ``json_schema_extra`` 
definition to control PICLE behavior. 

``json_schema_extra`` PICLE parameters:

- ``function`` - refers to ``@staticmethod`` of the model to call with command arguments
- ``presence`` - command argument set to ``presence`` value if command given
- ``processors`` - list of functions to run results of each command through one by one
- ``outputter`` - function to output results, by default results written to 
	stdout, Field's ``outputter`` overrides PicleConfig's ``outputter``
- ``outputter_kwargs`` - dictionary containing any additional argument to use with outputter
- ``multline`` - True/False, indicates if multi line input mode is enabled for this field

### Field processors

Processors allow to pass command execution results through a list of arbitrary functions.
Results returned by processor function passed on as input to next processor function in the 
list and so on.

In example below results returned by ``produce_structured_data`` function passed through
pprint formatter ``Formatters.formatter_pprint`` function to produce pretty formatted string.

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

### Multi Line Input

Mutli line input allows to read multiple lines of text into field value if 
json_schema_exatra ``multiline`` argument is set to ``True``. To use it need
to specify ``input`` as a field value on the command line, that will trigger
multi line input collection when hit return:

Sample model that has multi line input enabled:

```
class model_TestMultilineInput(BaseModel):
    data: StrictStr = Field(None, description="Multi line string", json_schema_extra={"multiline": True})
    arg: Any = Field(None, description="Some field")
    
    @staticmethod
    def run(**kwargs):
        return kwargs
```

This is how help will look like for ``data`` field:

```
picle#test_multiline_input data ?
 <'data' value>    Multi line string
 input             Collect value using multi line input mode
picle#
```

Tab completion for ``input`` value also works. On hitting ``enter``, 
mutli line input mode will be invoked:

```
picle#test_multiline_input data input arg foo
Enter lines and hit Ctrl+D to finish multi line input
I'am
Multi Line
Input
<ctrl+D hit>
```

## PICLE App

::: picle.App

## PICLE Build In Models

::: picle.models.Filters
::: picle.models.Formatters
::: picle.models.Outputters
::: picle.models.PipeFunctionsModel
