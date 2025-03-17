'''
The functions that generate the templates for the JSON files.
'''
from __future__ import annotations

ATTACHABLE_CUBE_GEO_ID = "geometry.cb2_cube"

def self_drop_loot_table_template(item_name: str) -> dict:
    return {
        "pools": [
            {
                "rolls": 1,
                "entries": [
                    {
                        "type": "item",
                        "name": item_name,
                        "functions": [
                            {
                                "function": "set_count",
                                "count": {
                                    "min": 1,
                                    "max": 1
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    }

def block_entity_behavior_template(namespace: str, name: str) -> dict:
    return {
        "format_version": "1.20.0",
        "minecraft:entity": {
            "description": {
                "identifier": f'{namespace}:{name}',
                "is_spawnable": True,
                "is_summonable": True,
                "animations": {
                    "place": f"controller.animation.cb2.{name}.place"
                },
                "scripts": {
                    "animate": ["place"]
                }
            },
            "component_groups": {
                "shapescape:despawn": {
                    "minecraft:instant_despawn": {}
                }
            },
            "components": {
                # Safety mechanism for additional despawning
                "minecraft:timer": {
                    "time": 0.5,
                    "time_down_event": {
                        "event": "shapescape:despawn",
                        "target": "self"
                    }
                },
                "minecraft:collision_box": {
                    "height": 0.0,
                    "width": 0.0
                },
                "minecraft:damage_sensor": {
                    "triggers": [
                        {
                            "deals_damage": False
                        }
                    ]
                }
            },
            "events": {
                "shapescape:despawn": {
                    "add": {
                        "component_groups": ["shapescape:despawn"]
                    }
                }
            }
        }
    }

def block_entity_entity_template(
        namespace: str, name: str, spawn_egg_texture_short_name: str) -> dict:
    return {
        "format_version": "1.20.0",
        "minecraft:client_entity": {
            "description": {
                "identifier": f"{namespace}:{name}",
                "spawn_egg": {
                    "texture": spawn_egg_texture_short_name
                }
            }
        }
    }

def block_entity_rotation_animation_controller_template(
        entity_name: str) -> tuple[str, dict]:
    '''
    Returns a tuple of a name of the animtion controller inside the animation
    controller file and its content.
    '''
    entity_name = f'controller.animation.cb2.{entity_name}.place'
    return entity_name, {
        "initial_state": "default",
        "states": {
            "default": {
                "transitions": [
                    {
                        "set_block": "1.0"
                    }
                ]
            },
            "set_block": {
                "on_entry": [],
            }
        }
    }

def attachable_hold_animation_template(
        name_suffix: str,
        position: list[str | int | float],
        rotation: list[str | int | float],
        scale: list[str | int | float]):
    return f'animation.cb2.{name_suffix}', {
        "bones": {
            "root": {
                "position": position,
                "rotation": rotation,
                "scale": scale
            }
        },
        "loop": True
    }

def terrain_texture():
    '''
    A template of the terrain_texture.json. Used only if the file doesn't
    exist.
    '''
    return {
        "texture_name": "atlas.terrain",
        "resource_pack_name": "vanilla",
        "padding": 8,
        "num_mip_levels": 4,
        "texture_data": {}
    }

def attachable_template(
        full_name: str,
        geometry: str, texture: str,
        first_person_anim: str,
        third_person_anim: str,
        material: str="entity_alphatest"):
    return {
        "format_version": "1.10.0",
        "minecraft:attachable": {
            "description": {
                "identifier": full_name,
                "materials": {
                    "default": material
                },
                "geometry": {
                    "default": geometry
                },
                "textures": {
                    "default": texture
                },
                "animations": {
                    "hold_1st_person": first_person_anim,
                    "hold_3rd_person": third_person_anim
                },
                "scripts": {
                    "animate": [
                        {"hold_1st_person": "c.is_first_person"},
                        {"hold_3rd_person": "!c.is_first_person"}
                    ]
                },
                "render_controllers": [f"controller.render.default"]
            }
        }
    }

def attachable_cube_geo():
    '''
    Returns the geometry of the attachable cube. The geometry is always the
    same.
    '''
    return {
        "format_version": "1.16.0",
        "minecraft:geometry": [
            {
                "description": {
                    "identifier": ATTACHABLE_CUBE_GEO_ID,
                    "visible_bounds_width": 1.0,
                    "visible_bounds_height": 1.0,
                    "visible_bounds_offset": [0, 0, 0],
                    "texture_width": 64,
                    "texture_height": 32
                },
                "bones": [
                    {
                        "name": "root",
                        "pivot": [0, 0, 0],
                        "rotation": [0, 0, 0],
                        "binding": "'rightitem'",
                        "cubes": [
                                {
                                    "uv": [0.0, 0.0],
                                    "size": [16, 16, 16],
                                    "origin": [-8, 0, -8],
                                    "pivot": [0, 8, 0],
                                    "rotation": [0, 0, 0]
                                }
                        ]
                    }
                ]
            }
        ]
    }
