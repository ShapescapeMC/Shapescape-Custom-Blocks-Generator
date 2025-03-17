(configuration-settings)=
# Configuration Settings

## Defaults
Here are the default settings of the filter.

```json
{
    "filter": "shapescape_custom_blocks_generator",
    "settings": {
        "scope_path": "scope.json"
    }
}
```

- `scope_path: str` - a path to JSON file that diefines the scope of variables provided to the template files during their evaluation. This propery is merged with the scope provided in the `_scope.json` file of every blocks group and the default values`{'true': True, 'false': False, 'math': math, 'uuid': uuid, 'Path': pathlib.Path}` where math, pathlib and uuid are standard Python modules. The default value of this property is `shapescape_custom_blocks_generator/scope.json`. The path is relative to data folder in working directory of regolith.
