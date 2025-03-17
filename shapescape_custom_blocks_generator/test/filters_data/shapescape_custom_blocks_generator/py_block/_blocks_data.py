{
    "namespace": "shapescape",
    "blocks": {
        "py_block": {
            # This is an example block usin the Python block data file.
            "translation": "Example PY block",
            "self_drop": True,
            "sound": "wood",
            "recipe_template": "recipe_template.recipe.json",
            "recipe_template_override": {
                "pattern": ["C  ", "FCF", "F F"],
                "result": {
                    "count": 10
                }
            },
            "block_template": "block_template.block.json",
            "block_template_override": {
                "components": {
                    "minecraft:map_color": "#FFFFFF",
                    "minecraft:geometry": "geometry.chair",
                    "minecraft:material_instances": {
                        "*": {
                            "texture": "block2",
                            "render_method": "alpha_test"
                        }
                    }
                }
            },
            "variants": {
                # Example shows using comprehension for more compact code.
                "color": [
                    {
                        "translation": color.capitalize(),
                        "id_suffix": color[0],
                        "shared_variant": {
                            "minecraft:material_instances": {
                                "*": {
                                    "texture": color
                                }
                            }
                        }
                    } for color in ['red', 'green', 'blue']
                ]
            }
        }
    }
}
