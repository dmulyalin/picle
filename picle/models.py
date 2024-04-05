from typing import List, Union, Optional, Callable, Any
from pydantic import ValidationError, BaseModel, StrictStr, Field, StrictBool, StrictInt


class PipeFunctionsModel(BaseModel):
    """
    Collection of common pipe functions to use in PICLE shell modesl
    """
    include: Any = Field(None, description="Filter output by pattern inclusion", function="_include")
    exclude: Any = Field(None, description="Filter output by pattern exclusion", function="_exclude")
        
    class PicleConfig:
        pipe = "self"
        
    @staticmethod
    def include(data: Any, include: Any=None) -> str:
        """
        Filter data line by line using provided pattern. Returns
        only lines that contains requested ``include`` pattern.
               
        :param data: data to filter
        :param include: pattern to filter data
        """
        include = str(include)
        return "\n".join(
            [
                line for line in str(data).splitlines()
                if include in line
            ]
        )
        
    @staticmethod
    def exclude(data: Any, exclude: Any=None) -> str:
        """
        Filter data line by line using provided pattern. Returns
        only lines that does not contains requested ``exclude`` pattern.
                
        :param data: data to filter
        :param exclude: pattern to filter data
        """
        exclude = str(exclude)
        return "\n".join(
            [
                line for line in str(data).splitlines()
                if exclude not in line
            ]
        )
        
        
