# PICLE APIs Reference

## PicleConfig

Each Pydantic model can have ``PicleConfig`` subclass defined
with model configuration parameters:

- ``ruler`` - The character used to draw separator lines under the help-message headers. If empty, no ruler line is drawn, defaults is empty
- ``intro`` - A string to issue as an intro or banner
- ``prompt`` - command line shell prompt
- ``use_rich`` - Use Python Rich library to print results if set to `True`
- ``newline`` - newline character to use while printing output, default is ``\r\n``
- ``completekey`` - is the ``readline`` name of a completion key, defaults to ``tab``
- ``pipe`` - reference to Pydantic model class to use with ``|`` (pipe) to process the
	results with various functions, special values:
     - ``pipe = "self"`` instruct to use current model for piping results through
     - ``import.path.to.model`` python import string to model for piping results through
- ``processors`` - list of functions to run results of `first command` through one by one
- ``outputter`` - function to output results, by default results written to stdout
- ``outputter_kwargs`` - dictionary containing any additional argument to use with outputter

Sample ``PicleConfig`` definition:

```
from picle.models import PipeFunctionsModel, Outputters

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
		processors = [Outputters.outputter_json]
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
	stdout. Field's ``outputter`` overrides PicleConfig's ``outputter``
- ``outputter_kwargs`` - dictionary containing any additional argument to use with outputter
- ``multiline`` - True/False, indicates if multi line input mode is enabled for this field
- ``root_model`` - True/False, if True reference to PICLE App's root model passed on to
    the ``run`` method or to the ``function`` inside ``root_model`` argument
- ``picle_app`` - True/False, if True reference to PICLE App passed on to the ``run``
    method or to the ``function`` inside ``picle_app`` argument, useful if need to modify
    PICLE App in a runtime, for example mount or remove models

### Field processors

Processors allow to pass command execution results through a list of arbitrary functions.
Results returned by processor function passed on as input to next processor function in the
list and so on.

In example below results returned by ``produce_structured_data`` function passed through
pprint outputter ``Outputters.outputter_pprint`` function to produce pretty formatted string.

```
from picle.models import Outputters

class model_show(BaseModel):
    data_pprint: Any = Field(
        None,
        description="Show data using pprint outputter",
        json_schema_extra={
            "processors": [
                    Outputters.outputter_pprint
                ],
            "function": "produce_structured_data"
        }
    )

    @staticmethod
    def produce_structured_data():
        return {"some": {"dictionary": {"data": None}}, "more": {"dictionary": ["data"]}, "even": {"more": {"dictionary": "data"}}}
```

### Multi Line Input

Multi line input allows to read multiple lines of text into field value if
json_schema_extra ``multiline`` argument is set to ``True``. To use it need
to specify ``input`` as a field value on the command line, that will trigger
multi line input collection when hit return:

Sample model that has multi line input enabled:

```
class model_TestMultilineInput(BaseModel):
    data: StrictStr = Field(
		None,
		description="Multi line string",
		json_schema_extra={"multiline": True}
	)
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
multi line input mode will be invoked:

```
picle#test_multiline_input data input arg foo
Enter lines and hit Ctrl+D to finish multi line input
I'am
Multi Line
Input
<ctrl+D hit>
```

## Result Specific Outputters

Sometimes having outputter defined per model is not enough and depending on produced
result different outputter need to be used, in that case result specific outputter can
be provided in return to ``run`` function call by returning a tuple of
``(result, outputter function, outputter kwargs,)``, where ``outputter kwargs`` is
optional.

Example:

```
from picle.models import Outputters

class model_ResultSpecificOutputter(BaseModel):
    data: StrictStr = Field(None, description="Multi line string")
    arg: Any = Field(None, description="Some field")

    class PicleConfig:
		outputter = Outputters.outputter_rich_print
		outputter_kwargs = {"any": "extra_argument"}

    @staticmethod
    def run(**kwargs):
		if kwargs.get("args") == "json":
			return kwargs["data"], Outputters.outputter_rich_json, {}
		elif kwargs.get("args") == "table":
			return kwargs["data"], Outputters.outputter_rich_table
		else:
			return kwargs
```

In addition to ``PicleConfig`` outputter, depending on arguments provided  ``run``
function returns outputter function to use to output the result with optional
``outputter_kwargs`` as a third argument. By default, if return result is not a tuple,
outputter specified in ``PicleConfig`` is used.

!!! note

	Result specific outputters supported starting with PICLE version 0.7.0

## Mounting Models at a Runtime

Sometimes it is needed to dynamically add new shell commands to the app,
for that PICLE ``App`` has ``model_mount`` and ``model_remove`` methods.

Example how to mount Pydantic model to PICLE App at given path in a runtime.

```
from picle import App
from pydantic import BaseModel, StrictStr

class my_mount_model(BaseModel):
    param: StrictStr = Field(None, description="Param string")

    @staticmethod
    def run(**kwargs):
        return kwargs

# create PICLE Root model
class Root(BaseModel):
    command: StrictStr = Field(None, description="Some command string")

# instantiate PICLE App shell
shell = App(Root)

# mount model
shell.model_mount(my_mount_model, ["another_command"])

# remove model
shell.model_remove(["another_command"])

shell.close()
```

## PICLE App

::: picle.App

## PICLE Build In Models

::: picle.models.Filters
::: picle.models.Outputters
::: picle.models.PipeFunctionsModel
::: picle.models.MAN
