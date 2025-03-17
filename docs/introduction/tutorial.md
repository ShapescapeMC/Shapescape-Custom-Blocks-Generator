(tutorial)=
# Tutorial
This tutorial aims to teach you how to create simple blocks with variables. For a more in-depth look at the features of this filter, please refer to the {ref}`Usage<usage>` section.

## Setting Up the Filter
To set up the filter, follow these steps:


1. Follow the {ref}`Installation<installation>` instructions in this documentation.
2. Navigate to your filters' data directory. By default, it should be at `../regolith/filters_data/shapescape_custom_blocks_generator`.
3. Create a `scope.json` file (by default, the `scope.json` file should be a part of the filter's data directory, but you can change this location in the filter's configuration using the `data_path` property mentioned in the {ref}`Installation<installation>` section of the documentation).
4. Create a subdirectory for each block you want to create. For example, for this tutorial, we will create a `chair`, so let's create a chair subdirectory. You don't have to have a separate subdirectory for each block, but in this tutorial, we're goint to make only one block.

## Creating a `_scope.json` File
Every block group needs a `_scope.json` file. It's a file that defines varialbes used during the evaluation of the template files. We're not going to use it in this example but it's required to be present. Let's create a file called `_scope.json` inside our `chair` subdirectory. Here's how to set up the basic code structure of the file (an empty JSON object):

``` json
{}
```


## Creating a `_blocks_data.json` File

> **Note**
> The `_blocks_data.json` file can alternatively be replaced with the `_blocks_data.py` file. In that case the file is evaluated using the Python interpreter and the result is used as the `_blocks_data.json` file. This allows you to use Python code to generate the `_blocks_data.json` file. The `_blocks_data.py` file is not covered in this tutorial.

Each block group needs a `_blocks_data.json` file. Although it's possible to write all custom block data into one file, it's suggested to split it up into multiple `_blocks_data.json` files inside subdirectories to make it more convenient to read and reuse certain generated blocks. For our chair example, let's create a file called `_blocks_data.json` inside our `chair` subdirectory. Here's how to set up the basic code structure of the file:

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {}
  }
}
```
The `namespace` is just the namespace for all files using identifiers. You can set this to whatever you want. The `blocks` object is a dictionary with different blocks. For our example, we only want to create a chair block, so we leave it for now.

Let's give it a name. We can do that by adding the translation argument. 

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "Chair"
    }
  }
}
```

## Creating a Block Template
Now we can define a block template. Although this is optional, it's suggested to create one anyway, as this workflow improves the readability of the `_blocks_data.json` files. To create a block template, create a file in the subdirectory that we created earlier, named `chair_block_template.block.json`. Here's some basic code structure to get started:

``` json
{
  "format_version": "1.20.0",
  "minecraft:block": {
    "description": {
      "states": {}
    },
    "permutations": [],
    "components": {
      "minecraft:geometry": "geometry.awesome_chair",
      "minecraft:destructible_by_explosion": {
        "explosion_resistance": 0
      },
      "minecraft:destructible_by_mining": {
        "seconds_to_destroy": 1.0
      },
      "minecraft:light_dampening": 0,
      "minecraft:friction": 0.4,
      "minecraft:collision_box": {
        "size": "`size`"
      }
    }
  }
}
```
Block template files allow us to define variables inside our scope file. As you can see, we used a custom variable called "\`size\`". Variables are useful when we have common values that multiple block templates share. This way, we can update all values in one place at the same time. Let's quickly define that variable inside of `scope.json`:

``` json
{
  "size": [16, 16, 16]
}
```

Now we just need to reference the block template inside our `_blocks_data.json` file:

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "Chair",
      "block_template": "chair_block_template.block.json"
    }
  }
}
```

If we're using the template for multiple blocks in this subdirectory, we can override parts of the block template inside the `_blocks_data.json` file by using `block_template_override`. For example, we can set the map color for this block by adding the `minecraft:map_color` to the `block_template_override`:

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "Chair",
      "block_template": "chair_block_template.block.json",
      "block_template_override": {
         "components": {
             "minecraft:map_color": "#FFFFFF"
        }
      }
    }
  }
}
```

## Adding Sounds
To add sounds to our block, we need to subscribe them to a sound identifier that's specific to the block. These identifiers have certain sounds mapped to events such as placing, destroying, walking, or jumping on the block. Vanilla blocks use sound identifiers like "wood" or "metal". We can use the `sounds` object to define block sounds. Let's update the `_blocks_data.json` file with the following code:

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "Chair",
      "block_template": "chair_block_template.block.json",
      "block_template_override": {
         "components": {
             "minecraft:map_color": "#FFFFFF"
        }
      }
      "sounds": "wood"
    }
  }
}
```

Now that we've added sounds to our block, we can manually define the block mapping for the texture in the project's `block.json` file. Once you've run regolith, you'll be able to access the block using the give command. Your block is now ready to be used!

## Adding Rotations
To allow our chair block to rotate according to the direction it's placed in, we need to use the `rotation_type` argument. There are multiple rotation types, but the `rotate_front_vertical` option is suitable for our needs as it lets us rotate the block in all four cardinal directions. We'll update our `_blocks_data.json` file with the following code:

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "Chair",
      "block_template": "chair_block_template.block.json",
      "block_template_override": {
         "components": {
             "minecraft:map_color": "#FFFFFF"
        }
      }
      "sounds": "wood",
      "rotation_type": "rotate_front_vertical"
    }
  }
}
```

## Adding a Spawn Egg Texture
Next, we need to define a spawn egg texture for our block. We'll add the `spawn_egg_texture` property to the `block_entity_properties` object, which references an item definition inside the `item_definitions.json` file. Here's the updated `_blocks_data.json` file:

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "Chair",
      "block_template": "chair_block_template.block.json",
      "block_template_override": {
         "components": {
             "minecraft:map_color": "#FFFFFF"
        }
      }
      "sounds": "wood",
      "block_entity_properties": {
        "spawn_egg_texture": "chair"
      },
      "rotation_type": "rotate_front_vertical"
    }
  }
}
```

We can also define a unique placing sound for our chair block. By default, if the `place_sound` argument is not used, the filter uses the `use.` sound defined in the `sounds` object. In this case, we want our chair to sound like metal when used, so we'll add the `place_sound` property to the `block_entity_properties` object as follows:

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "Chair",
      "block_template": "chair_block_template.block.json",
      "block_template_override": {
         "components": {
             "minecraft:map_color": "#FFFFFF"
        }
      }
      "sounds": "wood",
      "block_entity_properties": {
        "spawn_egg_texture": "chair",
        "place_sound": "use.metal"
      },
      "rotation_type": "rotate_front_vertical"
    }
  }
}
```

## Creating a Recipe Template
Similar to the block template, we can define a recipe template. Again, similar to the block template, we just need to have the file inside the same folder as the `_blocks_data.json` file it will be referenced in. Recipes do not need to have a result, as this will be generated based on the block variants. Let's create a simple recipe:

``` json
{
  "format_version": "1.12",
  "minecraft:recipe_shaped": {
    "tags": [
      "crafting_table"
    ],
    "pattern": [
      "FSS",
      "F F" 
    ],
    "key": {
      "F": {
        "item": "minecraft:planks"
      },
      "S": {
        "item": "minecraft:wool"
      }
    }
  }
}
```

And let's add that to our block in `_blocks_data.json`:

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "Chair",
      "block_template": "chair_block_template.block.json",
      "block_template_override": {
         "components": {
             "minecraft:map_color": "#FFFFFF"
        }
      }
      "sounds": "wood",
      "block_entity_properties": {
        "spawn_egg_texture": "chair",
        "place_sound": "use.metal"
      },
      "rotation_type": "rotate_front_vertical",
      "recipe_template": "chair_template.recipe.json"
    }
  }
}
```

Similar to block templates, we can also override recipe parameters of our recipe template. The recipe_template_override expects code at the level of `minecraft:recipe_shaped`, `minecraft:recipe_shapeless`, `minecraft:recipe_furnace`, `minecraft:recipe_brewing_mix`, which means we can go straight ahead and, for example, change the pattern to have a backrest:

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "Chair",
      "block_template": "chair_block_template.block.json",
      "block_template_override": {
         "components": {
             "minecraft:map_color": "#FFFFFF"
        }
      }
      "sounds": "wood",
      "block_entity_properties": {
        "spawn_egg_texture": "chair",
        "place_sound": "use.metal"
      },
      "rotation_type": "rotate_front_vertical",
      "recipe_template": "chair_template.recipe.json",
      "recipe_template_override": {
        "pattern": [
          "F  ",
          "FSS",
          "F F" 
        ],
      }
    }
  }
}
```

Now we are again at the point where we can just run regolith on this and have a usable block that now can be crafted. But currently, it does not drop anything when we break it.

## Adding Block Drops
We can use the `self_drop` parameter to let the block drop itself. This is really convenient for blocks that are complicated and heavily using variants. If you want to implement custom loot tables for the block drop, you can do this as part of a component that you add to your `block.json` either using the template or the `block_template_override`. We just want the block to drop itself, so let's add the `self_drop` parameter to our `_blocks_data.json`:

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "Chair",
      "block_template": "chair_block_template.block.json",
      "block_template_override": {
         "components": {
             "minecraft:map_color": "#FFFFFF"
        }
      }
      "sounds": "wood",
      "block_entity_properties": {
        "spawn_egg_texture": "chair",
        "place_sound": "use.metal"
      },
      "rotation_type": "rotate_front_vertical",
      "recipe_template": "chair_template.recipe.json",
      "recipe_template_override": {
        "pattern": [
          "F  ",
          "FSS",
          "F F" 
        ],
      },
      "self_drop": true
    }
  }
}
```

## Adding Variants
To introduce more variation to our chair block, we'll utilize `variants`. A variant group comprises a collection of objects known as a variant. Let's incorporate two variant groups: "frame" for oak and spruce, and "cushion" for red and blue. Since we're employing variants, we must name our block appropriately based on the variants. We can accomplish this by inserting the variant group names inside `{}` within the `translation` argument of the block. Next, we can define the `translation` for the `variant`, which will then be inserted in the block name where we specified it:

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "{frame} Chair with {cushion} Cushion",
      "block_template": "chair_block_template.block.json",
      "block_template_override": {
         "components": {
             "minecraft:map_color": "#FFFFFF"
        }
      }
      "sounds": "wood",
      "block_entity_properties": {
        "spawn_egg_texture": "chair",
        "place_sound": "use.metal"
      },
      "rotation_type": "rotate_front_vertical",
      "recipe_template": "chair_template.recipe.json",
      "recipe_template_override": {
        "pattern": [
          "F  ",
          "FSS",
          "F F" 
        ],
      },
      "self_drop": true,
      "variants": {
        "frame": [
          {
            "translation": "Oak"
          },
          {
            "translation": "Spruce"
          }
        ],
        "cushion": [
          {
            "translation": "Red"
          },
          {
            "translation": "Blue"
          }
        ]
      }
    }
  }
}
```

Additionally, we can include an `id_suffix` for the spawn eggs definitions. The spawn egg for all variant combinations should be defined within the item_texture.json file with the following format: `[SPAWN EGG TEXTURE]_[FIRST VARIANT GROUP ID]_[SUFFIX_SECOND VARIANT GROUP ID]`. If we don't define the `id_suffix`, the index of the variant inside the variant group will be used instead.

For example, if we add the id_suffix "o" and "s" to oak and spruce respectively and leave out the id_suffix for the cushion, the spawn egg definition of an Oak chair with a Blue cushion would be "chair_o_1".

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "{frame} Chair with {cushion} Cushion",
      "block_template": "chair_block_template.block.json",
      "block_template_override": {
         "components": {
             "minecraft:map_color": "#FFFFFF"
        }
      }
      "sounds": "wood",
      "block_entity_properties": {
        "spawn_egg_texture": "chair",
        "place_sound": "use.metal"
      },
      "rotation_type": "rotate_front_vertical",
      "recipe_template": "chair_template.recipe.json",
      "recipe_template_override": {
        "pattern": [
          "F  ",
          "FSS",
          "F F" 
        ],
      },
      "self_drop": true,
      "variants": {
        "frame": [
          {
            "translation": "Oak",
            "id_suffix": "o"
          },
          {
            "translation": "Spruce",
            "id_suffix": "s"
          }
        ],
        "cushion": [
          {
            "translation": "Red"
          },
          {
            "translation": "Blue"
          }
        ]
      }
    }
  }
}
```

We can use the variant's component object to override components for that variant object. For instance, we can make the frame easier to destroy when using oak and harder when using spruce. We'll also override the frames used for crafting by adding the "recipe" component. Here's the updated `_blocks_data.json` file:

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "{frame} Chair with {cushion} Cushion",
      "block_template": "chair_block_template.block.json",
      "block_template_override": {
         "components": {
             "minecraft:map_color": "#FFFFFF"
        }
      }
      "sounds": "wood",
      "block_entity_properties": {
        "spawn_egg_texture": "chair",
        "place_sound": "use.metal"
      },
      "rotation_type": "rotate_front_vertical",
      "recipe_template": "chair_template.recipe.json",
      "recipe_template_override": {
        "pattern": [
          "F  ",
          "FSS",
          "F F" 
        ],
      },
      "self_drop": true,
      "variants": {
        "frame": [
          {
            "translation": "Oak",
            "id_suffix": "o",
            "components": {
              "minecraft:destructible_by_mining": {
                "seconds_to_destroy": 0.7
              },  
            },
            "recipe": {
              "key": {
                "F": { "item": "minecraft:oak_planks" }
              }
            },
          },
          {
            "translation": "Spruce",
            "id_suffix": "s",
            "components": {
              "minecraft:destructible_by_mining": {
                "seconds_to_destroy": 1.3
              },  
            },
            "recipe": {
              "key": {
                "F": { "item": "minecraft:spruce_planks" }
              }
            },
          }
        ],
        "cushion": [
          {
            "translation": "Red",
            "recipe": {
              "key": {
                "S": { "item": "minecraft:red_wool" }
              }
            },
          },
          {
            "translation": "Blue",
            "recipe": {
              "key": {
                "S": { "item": "minecraft:blue_wool" }
              }
            },
          }
        ]
      }        
    }
  }
}
```

Finally, we'll update the textures of our chair variants. We'll use the minecraft:material_instances component, but there is a caveat: Minecraft components do not merge together. To work around this, we'll use the `shared_variant` feature of the filter to merge the components properly.  You can read more about the merging in the {ref}`Block Files Generation<block-files-generation>` and {ref}`JSON Overriding<json-overriding>` documents. We'll define a component template in the shared variant objects and then override parts of these components inside the variants. Here's the final `_blocks_data.json` file:

``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "{frame} Chair with {cushion} Cushion",
      "block_template": "chair_block_template.block.json",
      "block_template_override": {
         "components": {
             "minecraft:map_color": "#FFFFFF"
        }
      }
      "sounds": "wood",
      "block_entity_properties": {
        "spawn_egg_texture": "chair",
        "place_sound": "use.metal"
      },
      "rotation_type": "rotate_front_vertical",
      "recipe_template": "chair_template.recipe.json",
      "recipe_template_override": {
        "pattern": [
          "F  ",
          "FSS",
          "F F" 
        ],
      },
      "self_drop": true,
      "shared_variants": {
        "minecraft:material_instances": {
          "*": {
            "texture": "frame",
            "render_method": "alpha_test"
          },
          "cushion": {
            "texture": "cushion",
            "render_method": "alpha_test"
          }
        }
      },
      "variants": {
        "frame": [
          {
            "translation": "Oak",
            "id_suffix": "o",
            "components": {
              "minecraft:destructible_by_mining": {
                "seconds_to_destroy": 0.7
              },  
            },
            "shared_variant": {
              "minecraft:material_instances": {
                "*": {
                  "texture": "oak_chair"
                }
              }
            }
          },
          {
            "translation": "Spruce",
            "id_suffix": "s",
            "components": {
              "minecraft:destructible_by_mining": {
                "seconds_to_destroy": 1.3
              },  
            },
            "shared_variant": {
              "minecraft:material_instances": {
                "*": {
                  "texture": "spruce_chair"
                }
              }
            }
          }
        ],
        "cushion": [
          {
            "translation": "Red",
            "shared_variant": {
              "minecraft:material_instances": {
                "cushion": {
                  "texture": "chair_cushion_red"
                }
              }
            }
          },
          {
            "translation": "Blue",
            "shared_variant": {
              "minecraft:material_instances": {
                "cushion": {
                  "texture": "chair_cushion_blue"
                }
              }
            }
          }
        ]
      }
    }
  }
}
```

With these changes, our chair block is now fully functional and comes with several variants for players to choose from!

## Adding attachable

Attachables are added by defining "attachable" in the block_entity_properties. An example is shown below:
```json
// ...
"attachable": {
  "assets": {
    "texture": "TERRAIN_TEXTURE:oak_chair",
    "geometry": "geometry.awesome_chair",
  }
}
```

The prefix "TERRAIN_TEXTURE:" in the texture definition means that the filter should look for the texture in the `terrain_texture.json` file of the resource pack. If the path doesn't exist you will get an error. There are other alternative ways to define models and textures, but they are not covered in this tutorial. You can read about them in the {ref}`Usage<usage>` section of the documentation.

Here is a complete file example:
``` json
{
  "namespace": "my_custom_blocks",
  "blocks": {
    "chair": {
      "translations": "{frame} Chair with {cushion} Cushion",
      "block_template": "chair_block_template.block.json",
      "block_template_override": {
         "components": {
             "minecraft:map_color": "#FFFFFF"
        }
      }
      "sounds": "wood",
      "block_entity_properties": {
        "spawn_egg_texture": "chair",
        "place_sound": "use.metal",
        "attachable": {
          "assets": {
            "texture": "TERRAIN_TEXTURE:oak_chair",
            "geometry": "geometry.awesome_chair",
          }
        }
      },
      "rotation_type": "rotate_front_vertical",
      "recipe_template": "chair_template.recipe.json",
      "recipe_template_override": {
        "pattern": [
          "F  ",
          "FSS",
          "F F" 
        ],
      },
      "self_drop": true,
      "shared_variants": {
        "minecraft:material_instances": {
          "*": {
            "texture": "frame",
            "render_method": "alpha_test"
          },
          "cushion": {
            "texture": "cushion",
            "render_method": "alpha_test"
          }
        }
      },
      "variants": {
        "frame": [
          {
            "translation": "Oak",
            "id_suffix": "o",
            "components": {
              "minecraft:destructible_by_mining": {
                "seconds_to_destroy": 0.7
              },  
            },
            "shared_variant": {
              "minecraft:material_instances": {
                "*": {
                  "texture": "oak_chair"
                }
              }
            }
          },
          {
            "translation": "Spruce",
            "id_suffix": "s",
            "components": {
              "minecraft:destructible_by_mining": {
                "seconds_to_destroy": 1.3
              },  
            },
            "shared_variant": {
              "minecraft:material_instances": {
                "*": {
                  "texture": "spruce_chair"
                }
              }
            }
          }
        ],
        "cushion": [
          {
            "translation": "Red",
            "shared_variant": {
              "minecraft:material_instances": {
                "cushion": {
                  "texture": "chair_cushion_red"
                }
              }
            }
          },
          {
            "translation": "Blue",
            "shared_variant": {
              "minecraft:material_instances": {
                "cushion": {
                  "texture": "chair_cushion_blue"
                }
              }
            }
          }
        ]
      }
    }
  }
}
```
