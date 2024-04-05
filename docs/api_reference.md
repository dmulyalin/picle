# PICLE APIs Reference

## PicleConfig Attributes Reference

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

## PICLE APP API

::: picle.App

## PICLE Build In Models

### PipeFunctionsModel

::: picle.models.PipeFunctionsModel
