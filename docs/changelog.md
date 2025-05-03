# 0.9.0

## CHANGES

1. Removed support for using `Callable` annotation for calling model method
2. Removed formatters from built in models, instead need to use outputter
3. Improved pipe functions handling logic 
4. Rich is now a default outputter, can be disabled using ``use_rich`` config parameter in the root's model PicleConfig 
## FEATURES

1. Added Tabulate table outputter
2. Added `save` outputter to save results into a file
3. Added support for pipe attribute to reference `path.to.pipemodel` Python import string
