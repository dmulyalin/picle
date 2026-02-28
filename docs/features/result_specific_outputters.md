# Result-specific Outputters

Sometimes a single model-level outputter is not enough. If you need to choose an outputter based on runtime data,
return a tuple from `run()`:

```
(result, outputter)
(result, outputter, outputter_kwargs)
```

This overrides model and field outputters for that specific execution.