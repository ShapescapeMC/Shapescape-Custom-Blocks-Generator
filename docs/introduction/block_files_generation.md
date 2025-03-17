(block-files-generation)=
# Block files generation

This page describes in detail how the `BP/blocks/*.block.json` files are generated and how their contents can be controlled by overriding with data defined in certain files defined in the filter configuration.

## Main components of the file

The main structure of the block file is based on two sources:
- template file - the file defined in the `block_template` property of the block definition.
- the content of the `block_template_override` property.

First, the template file is evaluated using the data from the `scope.json` file and than the content of the block_template_override is placed on top of the the template file using the json overriding. The process of the evaluation uses the [regolith-json-template](https://github.com/Nusiq/regolith-json-template) Python module.

You can learn more about using the module on the [json_template regolith filter Github page](https://github.com/Nusiq/regolith-filters/tree/master/json_template). In short, the module allows you to use variables in the JSON file by replacing them with values defined in the `scope.json` file. The variables are defined as strings that start and end with backticks "`` ` ``".

## Variants

The filter allows you to define block variants which in the output are defined using custom properties and permutations. You can read more about properties and permutations in the official [Minecraft Bedrock Creator documentation](https://learn.microsoft.com/en-us/minecraft/creator/reference/content/blockreference/examples/blockpropertiesandpermutations)

In the `_blocks_data.json` file in the block definition, the variants are defined in the `variants` property. The variants property is an object where the keys are the names of the groups of variants and the values are lists of the variants in every group. Inside every variant, there is a `components` property which is directly copied into the block file as a content of the permutation. The molang query for the `condition` property in the generated block is created automatically.

The filter creates custom entities whose spawn eggs can be used in order to spawn every possible combination of variants using a product of the variants in every variant group.

## Shared variants

Shared variants are the variants automatically created based on the product of the variants in every variant group. For example if you create a chair block with 3 types of frames and 2 types of cushions, the filter will create 6 shared variants. Every combination must be hardcoded so keep in mind that the number of shared variants can grow very fast. The shared varaints are created based on two sources:

- The `shared_variants` property in the block definition (`_blocks_data.json -> "blocks" -> "[block]" -> "shared_variants"`).
- The `shared_variants` property in every variant of every variant group (`_blocks_data.json -> "blocks" -> [block] -> "shared_variants" -> "variants" -> [variant group] -> [variant] -> "shared_variants"`).

The values are combined for every shared variant by using the JSON override. The `shared_variant` of the block is placed on the bottom and than for every variant group, the `shared_variant` of the variant is placed on top of the block `shared_variant` in the order as they are defined in the `_blocks_data.json` file.


```{warning}
As you can see in the section above, the order of defining variant groups in the `variant` property matters. It defines which variant group is placed on top of the other. The first variant group is placed on the bottom and the last one is placed on top, overriding the properties of the previous variant gruops.
```

The main `shared_variants` property is just for your convinience, so you don't have to redefine the same properties for every variant. If the block doesn't have any variants, the `shared_variants` property is ignored.
