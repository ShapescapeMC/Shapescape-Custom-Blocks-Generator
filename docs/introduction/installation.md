(installation)=
# Installation

## Steps

### 1. Install the filter
Use the following command
```
regolith install shapescape_custom_blocks_generator
```

You can alternatively use this command:
```
regolith install github.com/ShapescapeMC/Shapescape-Custom-Blocks-Generator/shapescape_custom_blocks_generator
```

### 2. Add filter to a profile
Add the filter to the `filters` list in the `config.json` file of the Regolith project and add the settings:

```json
{
    "filter": "shapescape_custom_blocks_generator",
}
```