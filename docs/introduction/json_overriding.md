(json-overriding)=
# JSON overriding

JSON overriding is a concept widely used in the `shapescape_custom_blocks_generator` filter. It allows you to merge multiple JSON objects into one.

## Examples

Following examples show how the JSON overriding works, the `A` object in all of the examples is always the object that is being overridden. That means that "the `B` object is placed on top of the `A` object".

### Example 1 - Primitive  properties

A:
```json
{
    "a": 1,
    "b": 2,
    "c": 3
}
```

B:
```json
{
    "a": "a",
    "b": "b"
}
```

Result:
```json
{
    "a": "a",
    "b": "b",
    "c": 3
}
```

### Example 2 - Lists

A:
```json
{
    "a": [1, 2, 3],
    "b": [4, 5, 6]
}
```

B:
```json
{
    "a": ["a", "b", "c"],
    "b": ["a", "b"]
}
```

Result:
```json
{
    "a": ["a", "b", "c"],
    "b": ["a", "b", 6]
}
```

### Example 3 - nested objects

A:
```json
{
    "a": {
        "a": 1,
        "b": 2
    },
    "b": {
        "a": 3,
        "b": 4
    }
}
```

B:
```json
{
    "a": {
        "a": "a"
    },
    "b": "b"
}
```

Result:
```json
{
    "a": {
        "a": "a",
        "b": 2
    },
    "b": "b"
}
```