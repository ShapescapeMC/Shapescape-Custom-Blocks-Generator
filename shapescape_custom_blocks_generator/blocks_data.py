'''
This module contains the BlocksData class and the objects used for navigating the
_blocks_data.json file.
'''
from __future__ import annotations

import json
import os
from functools import cached_property, cache
from json import JSONDecodeError
from pathlib import Path
from textwrap import dedent, indent
from typing import Any, Literal, Iterator, NamedTuple

from better_json_tools import load_jsonc
from better_json_tools.compact_encoder import CompactEncoder
from better_json_tools.json_walker import JSONWalker
from errors import CustomBlocks2Error, print_red, print_yellow
from merge import deep_merge_objects
from regolith_json_template import eval_json
from json_templates import (
    self_drop_loot_table_template, block_entity_behavior_template,
    block_entity_entity_template,
    block_entity_rotation_animation_controller_template, terrain_texture,
    attachable_hold_animation_template, attachable_cube_geo,
    attachable_template, ATTACHABLE_CUBE_GEO_ID)
from PIL import Image
from itertools import product
from copy import deepcopy, copy
from collections import defaultdict

# The transformations used in the 1st person attachable hold animations
ATTACHABLE_HOLD_3RD_PERSON_POSITION = (0, 18, -4)
ATTACHABLE_HOLD_3RD_PERSON_ROTATION = (31, -47, -20)
ATTACHABLE_HOLD_3RD_PERSON_SCALE = (0.35, 0.35, 0.35)
# The transformations usedi n the 3rd person attachable hold animaitons
ATTACHABLE_HOLD_1ST_PERSON_POSITION = (-4, 29, -4)
ATTACHABLE_HOLD_1ST_PERSON_ROTATION = (-128, -131, 3)
ATTACHABLE_HOLD_1ST_PERSON_SCALE = (0.35, 0.35, 0.35)

CAN_PLACE_BLOCKS = ('air', 'tallgrass', 'water', 'lava')
'''A list of blocks that don't block block placement inside them.'''

BLOCK_ROTATION_TRANSFORMATION_MAP = {
    "zp_front": [0, 180, 0],
    "zm_front": [0, 0, 0],
    "yp_front": [90, 0, 0],
    "ym_front": [-90, 0, 0],
    "xp_front": [0, -90, 0],
    "xm_front": [0, 90, 0],

    "zp_top": [90, 0, 0],
    "zm_top": [-90, 0, 0],
    "yp_top": [0, 0, 0],
    "ym_top": [180, 0, 0],
    "xp_top": [0, 0, -90],
    "xm_top": [0, 0, 90],
}
'''
The map of easy to read names of block rotations to the actual rotasions used
in the transformation component to rotate the block.
'''

RP_PATH = Path("RP")

class CubicAttachableTextureSides(NamedTuple):
    '''
    An object with the paths to the textures for each side of the cubic
    attachable
    '''
    north: Path
    south: Path
    east: Path
    west: Path
    up: Path
    down: Path

class MolangVector3D(NamedTuple):
    '''
    A 3D vector that uses molang or numbers and could be used in the
    animations.
    '''
    x: str | float | int
    y: str | float | int
    z: str | float | int

    @staticmethod
    def new(data: list[str | float | int]):
        '''
        Creates a new MolangVector3D object and validates the arguments in
        the process.
        '''
        if not isinstance(data, list):
            raise CustomBlocks2Error('The vector must be a list.')
        if len(data) != 3:
            raise CustomBlocks2Error('The vector must have 3 elements.')
        for v in data:
            if not isinstance(v, (int, float, str)):
                raise CustomBlocks2Error(
                    'Every element of the vector must be int, float or str.')
        return MolangVector3D(data[0], data[1], data[2])

    def as_list(self):
        return [self.x, self.y, self.z]

class WdSwitch:
    '''
    A context manager that switches the working directory to the specified path
    '''
    def __init__(self, path: Path):
        self.path = path
        self.old_path = Path.cwd()

    def __enter__(self):
        os.chdir(self.path)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self.old_path)

class TerrainTexture:
    '''
    A class that represents the terrain_texture.json file.
    '''
    PATH = Path("RP/textures/terrain_texture.json")

    @staticmethod
    @cache
    def get() -> TerrainTexture:
        if not TerrainTexture.PATH.exists():
            data = terrain_texture()
            return TerrainTexture(JSONWalker(data))
        try:
            return TerrainTexture(load_jsonc(TerrainTexture.PATH))
        except (JSONDecodeError, OSError) as e:
            raise CustomBlocks2Error(dedent(f'''\
                Failed to load the terrain_texture.json file.
                Path: {TerrainTexture.PATH.as_posix()}
                '''))

    def __init__(self, data: JSONWalker):
        self.data = data

    def has_key(self, key: str) -> bool:
        return (self.data / 'texture_data' / key / 'textures').exists

    def get_texture_path_identifier(self, key: str) -> str:
        '''
        Gets minecraft-style texture path/identifier (the path relative to the
        'RP' folder without the extension). The method doens't check if the
        texture exists or if it's a valid texture path. It only makes sure that
        it's a string from the terrain_texture.json file.
        exists.
        '''
        texture_walker = self.data / 'texture_data' / key / 'textures'
        if not texture_walker.exists:
            raise CustomBlocks2Error(dedent(f'''\
                The texture doesn't exists in the terrain_texture.json file.
                terrain_texture.json key: {key}
                Path: {TerrainTexture.PATH.as_posix()}
                JSON Path: {texture_walker.path_str}
                '''))
        if not isinstance(texture_walker.data, str):
            raise CustomBlocks2Error(dedent, f'''\
                The texture path must be a string.
                terrain_texture.json key: {key}
                Path: {TerrainTexture.PATH.as_posix()}
                JSON Path: {texture_walker.path_str}
                ''')
        return texture_walker.data

class Lang:
    '''
    A singleton class that provides the access to the en_us.lang file
    '''
    PATH = Path("RP/texts/en_US.lang")

    @staticmethod
    @cache
    def get() -> Lang:
        try:
            with Lang.PATH.open('r', encoding='utf-8-sig') as f:
                data: list[str] = f.readlines()
                known_keys = {
                    line.split('=', 1)[0] for line in data if '=' in line}
        except OSError:
            data = []
            known_keys: set[str] = set()
        return Lang(data, known_keys)

    def save_if_not_empty(self):
        if len(self.data) == 0:
            return
        Lang.PATH.parent.mkdir(parents=True, exist_ok=True)
        with Lang.PATH.open('w', encoding='utf-8') as f:
            f.writelines(self.data)
        Lang.get.cache_clear()

    def __init__(self, data: list[str], known_keys: set[str]):
        self.data = data
        self.known_keys = known_keys

    def add(self, key: str, value: str):
        if key in self.known_keys:
            print_red(
                f"Skipped adding the translation key '{key}' to the lang file "
                f"because it already exists.")
        if len(self.data) > 0 and not self.data[-1].endswith('\n'):
            self.data.append('\n')
        self.data.append(f'{key}={value}\n')

class RpBlocksJson:
    '''
    A singleton class that provides access to the blocks.json file in the
    resource pack.
    '''
    PATH = Path("RP/blocks.json")

    @staticmethod
    @cache
    def get() -> RpBlocksJson:
        try:
            with RpBlocksJson.PATH.open('r', encoding='utf-8') as f:
                data = json.load(f)
        except (JSONDecodeError, OSError):
            data = {"format_version": [1, 16, 0]}
        return RpBlocksJson(data)

    def save_if_not_empty(self):
        data = self.walker.data
        if not isinstance(data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The blocks.json file must be a dict.
                Path: {RpBlocksJson.PATH.as_posix()}'''))

        if 'format_version' in data:
            if len(data) == 1:
                return
        else:
            if len(data) == 0:
                return

        RpBlocksJson.PATH.parent.mkdir(parents=True, exist_ok=True)
        with RpBlocksJson.PATH.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent='\t', cls=CompactEncoder)
        RpBlocksJson.get.cache_clear()

    def add_block(self, block: _Block):
        this_block_config = self.walker / block.full_name
        if this_block_config.exists and not isinstance(
                this_block_config.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The blocks in the blocks.json file must be a dict.
                Path: {RpBlocksJson.PATH.as_posix()}
                JSON Path: {this_block_config.path_str}'''))
        this_block_sound = this_block_config / 'sound'
        if this_block_sound.exists:
            raise CustomBlocks2Error(dedent(f'''\
                The sound of the block is already defined in the blocks.json file.
                Path: {RpBlocksJson.PATH.as_posix()}
                JSON Path: {this_block_sound.path_str}'''))

        # We know that the parent path is a dictionary and that the key doens't
        # exist yet so it's safe to create a new one without any additional
        # error handling.
        this_block_sound.create_path(
            block.sound,
            exists_ok=False,
            can_break_data_structure=False,
            can_create_empty_list_items=False
        )
        if block.texture is not None:
            (this_block_config / 'textures').create_path(
                block.texture,
                exists_ok=False,
                can_break_data_structure=False,
                can_create_empty_list_items=False
            )

    def __init__(self, data: dict[str, Any]):
        self.walker: JSONWalker = JSONWalker(data)

class BpAnimationControllerJson:
    '''
    A singleton that represents the animation controller file used by the
    block entities.
    '''
    PATH = Path("BP/animation_controllers/cb2.bp_ac.json")

    @staticmethod
    @cache
    def get() -> BpAnimationControllerJson:
        try:
            with BpAnimationControllerJson.PATH.open('r', encoding='utf-8-sig') as f:
                data = json.load(f)
        except (JSONDecodeError, OSError):
            data = {"format_version": "1.19.0", "animation_controllers": {}}
        return BpAnimationControllerJson(data)

    def save_if_not_empty(self):
        if not isinstance(self.walker.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The block entity animation controller file must be a dict.
                Path: {BpAnimationControllerJson.PATH.as_posix()}'''))
        acs = (
            self.walker / 'animation_controllers')
        if not acs.exists:
            return
        if not isinstance(acs.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The animation_controllers property must be a dict.
                Path: {BpAnimationControllerJson.PATH.as_posix()}
                JSON Path: {acs.path_str}'''))
        if len(acs.data) == 0:
            return

        BpAnimationControllerJson.PATH.parent.mkdir(parents=True, exist_ok=True)
        with BpAnimationControllerJson.PATH.open('w', encoding='utf-8') as f:
            json.dump(
                self.walker.data, f, indent='\t',
                cls=CompactEncoder)
        BpAnimationControllerJson.get.cache_clear()

    def __init__(self, data: dict[str, Any]):
        self.walker: JSONWalker = JSONWalker(data)

    def add_animation_controller(self, ac_name: str, data: dict):
        name_walker = self.walker / 'animation_controllers' / ac_name
        try:
            name_walker.create_path(
                data,
                can_break_data_structure=False,
                can_create_empty_list_items=False,
                exists_ok=False)
        except (ValueError, KeyError) as e:
            raise CustomBlocks2Error(dedent(f'''\
                Failed to add the animation controller.
                Path: {BpAnimationControllerJson.PATH.as_posix()}
                Animation Controller Name: {ac_name}
                Error: {str(e)}'''))

    def _generate_any_rotation(self,  block_entity: _BlockEntity, place_block_commands: list[str]) -> None:
        '''
        Helper functions for all of the functions that generate the block
        rotations to reduce code duplication.
        '''
        ac_name, ac_data = block_entity_rotation_animation_controller_template(
            block_entity.name)

        # Add commands to the animation controller
        ac_data['states']['set_block']['on_entry'] = [
            # Make sure that the entity is facing the nearest player
            # this is not a perfect solution but it covers most of the cases
            # this could be improved by tagging the player that places the
            # block.
            "/tp @s ~ ~ ~ facing @p",
        ] + [
            # Check if the block can be placed
            f'/execute if block ~ ~ ~ {block} run tag @s add can_place'
            for block in CAN_PLACE_BLOCKS
        ] + [
            # Give the spawn egg back to the player if the block can't be
            # placed
            f'/execute unless entity @s[tag=can_place] run '
            f'give @p {block_entity.parent.full_name}_spawn_egg',

            # Play block placing sound
            f'/execute if entity @s[tag=can_place] run '
            f'playsound  {block_entity.place_sound} @a ~ ~ ~ 1 1',
        ] + place_block_commands + [

            # Despawn self
            '@s despawn'
        ]
        self.add_animation_controller(ac_name, ac_data)

    def generate_no_rotation(self, block_entity: _BlockEntity) -> None:
        place_block_commands = [
            # Spawn the block
            f'/execute if entity @s[tag=can_place] run '
            f'setblock ~ ~ ~ '
            f'{block_entity.parent.full_name}[{block_entity.block_data_items}]'
        ]
        self._generate_any_rotation(block_entity, place_block_commands)

    def generate_align_xyz_bp_ac(self, block_entity: _BlockEntity) -> None:
        place_block_commands = [
            # Get the rotation
            "/tag @s[rxm=-90,rx=-60] add y_aligned",
            "/tag @s[rxm=60,rx=90] add y_aligned",
            "/tag @s[tag=!y_aligned,rym=135,ry=180] add z_aligned",
            "/tag @s[tag=!y_aligned,ry=-135,rym=-180] add z_aligned",
            "/tag @s[tag=!y_aligned,rym=-45,ry=45] add z_aligned",
            "/tag @s[tag=!y_aligned,tag=!z_aligned,rym=45,ry=135] add x_aligned",
            "/tag @s[tag=!y_aligned,tag=!z_aligned,rym=-135,ry=-45] add x_aligned",
            # Spawn the block
            # x_aligned
            f'/execute if entity @s[tag=can_place,tag=x_aligned] run '
            f'setblock ~ ~ ~ '
            f'{block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(0)}]',
            # y_aligned
            f'/execute if entity @s[tag=can_place,tag=y_aligned] run '
            f'setblock ~ ~ ~ '
            f'{block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(1)}]',
            # z_aligned
            f'/execute if entity @s[tag=can_place,tag=z_aligned] run '
            f'setblock ~ ~ ~ '
            f'{block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(2)}]',
        ]
        self._generate_any_rotation(block_entity, place_block_commands)

    def generate_align_xz_bp_ac(self, block_entity: _BlockEntity) -> None:
        place_block_commands = [
            # Get the rotation
            "/tag @s[tag=!y_aligned,rym=135,ry=180] add z_aligned",
            "/tag @s[tag=!y_aligned,ry=-135,rym=-180] add z_aligned",
            "/tag @s[tag=!y_aligned,rym=-45,ry=45] add z_aligned",
            "/tag @s[tag=!y_aligned,tag=!z_aligned,rym=45,ry=135] add x_aligned",
            "/tag @s[tag=!y_aligned,tag=!z_aligned,rym=-135,ry=-45] add x_aligned",
            # Spawn the block
            # x_aligned
            f'/execute if entity @s[tag=can_place,tag=x_aligned] run '
            f'setblock ~ ~ ~ '
            f'{block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(0)}]',
            # z_aligned
            f'/execute if entity @s[tag=can_place,tag=z_aligned] run '
            f'setblock ~ ~ ~ '
            f'{block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(1)}]',
        ]
        self._generate_any_rotation(block_entity, place_block_commands)

    def generate_rotate_vertical_bp_ac(self, block_entity: _BlockEntity) -> None:
        place_block_commands = [
            # Get the rotation
            "/tag @s[rym=135,ry=180] add zm",
            "/tag @s[ry=-135,rym=-180] add zm",
            "/tag @s[tag=!zm,rym=-45,ry=45] add zp",
            "/tag @s[tag=!zm,tag=!zp,rym=45,ry=135] add xm",
            "/tag @s[tag=!zm,tag=!zp,tag=!xm,rym=-135,ry=-45] add xp",
            # Spawn the block
            # xp
            f'/execute if entity @s[tag=can_place,tag=xp] run '
            f'setblock ~ ~ ~ '
            f'{block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(0)}]',
            # xm
            f'/execute if entity @s[tag=can_place,tag=xm] run '
            f'setblock ~ ~ ~ '
            f'{block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(1)}]',
            # zp
            f'/execute if entity @s[tag=can_place,tag=zp] run '
            f'setblock ~ ~ ~ '
            f'{block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(2)}]',
            # zm
            f'/execute if entity @s[tag=can_place,tag=zm] run '
            f'setblock ~ ~ ~ '
            f'{block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(3)}]',
        ]
        self._generate_any_rotation(block_entity, place_block_commands)

    def generate_rotate_both_bp_ac(self, block_entity: _BlockEntity) -> None:
        place_block_commands = [
            # Get the rotation
            "/tag @s[rxm=-90,rx=-60] add yp",
            "/tag @s[tag=!yp,rxm=60,rx=90] add ym",
            "/tag @s[tag=!yp,tag=!ym,rym=135,ry=180] add zm",
            "/tag @s[tag=!yp,tag=!ym,ry=-135,rym=-180] add zm",
            "/tag @s[tag=!yp,tag=!ym,tag=!zm,rym=-45,ry=45] add zp",
            "/tag @s[tag=!yp,tag=!ym,tag=!zm,tag=!zp,rym=45,ry=135] add xm",
            "/tag @s[tag=!yp,tag=!ym,tag=!zm,tag=!zp,tag=!xm,rym=-135,ry=-45] add xp",
            # Spawn the block
            # xp
            f'/execute if entity @s[tag=can_place,tag=xp] run '
            f'setblock ~ ~ ~ {block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(0)}]',
            # xm
            f'/execute if entity @s[tag=can_place,tag=xm] run '
            f'setblock ~ ~ ~ {block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(1)}]',
            # yp
            f'/execute if entity @s[tag=can_place,tag=yp] run '
            f'setblock ~ ~ ~ {block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(2)}]',
            # ym
            f'/execute if entity @s[tag=can_place,tag=ym] run '
            f'setblock ~ ~ ~ {block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(3)}]',
            # zp
            f'/execute if entity @s[tag=can_place,tag=zp] run '
            f'setblock ~ ~ ~ {block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(4)}]',
            # zm
            f'/execute if entity @s[tag=can_place,tag=zm] run '
            f'setblock ~ ~ ~ {block_entity.parent.full_name}'
            f'[{block_entity.get_block_data_items_with_rotation(5)}]',
        ]
        self._generate_any_rotation(block_entity, place_block_commands)

class RpAttachableAnimationJson:
    '''
    A singleton that represents the file with the hold animations for the
    attachables.
    '''
    PATH = Path("RP/animations/cb2.animation.json")
    '''The path to the file with the hold animations for the attachables.'''

    @staticmethod
    @cache
    def get() -> RpAttachableAnimationJson:
        try:
            data = load_jsonc(RpAttachableAnimationJson.PATH)
        except (JSONDecodeError, OSError):
            data = JSONWalker({"format_version": "1.8.0", "animations": {}})
        return RpAttachableAnimationJson(data)

    def save_if_not_empty(self):
        if not isinstance(self.walker.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The attachable hold animation file must be a dict.
                Path: {RpAttachableAnimationJson.PATH.as_posix()}'''))
        anims = (
            self.walker / 'animations')
        if not anims.exists:
            return
        if not isinstance(anims.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The animations property must be a dict.
                Path: {RpAttachableAnimationJson.PATH.as_posix()}
                JSON Path: {anims.path_str}'''))
        if len(anims.data) == 0:
            return

        RpAttachableAnimationJson.PATH.parent.mkdir(
            parents=True, exist_ok=True)
        with RpAttachableAnimationJson.PATH.open('w', encoding='utf-8') as f:
            json.dump(
                self.walker.data, f, indent='\t',
                cls=CompactEncoder)
        RpAttachableAnimationJson.get.cache_clear()


    def __init__(self, data: JSONWalker):
        self.walker: JSONWalker = data
        self.animation_counter = 0
        '''Used for generating unique identifiers for the animations.'''

    @cache
    def generate_hold_animation(
            self, position: MolangVector3D, rotation: MolangVector3D,
            scale: MolangVector3D) -> str:
        '''
        Generates the hold animation for the attachable and returns its
        identifier to be used in when the attachable is being held.
        '''
        index = self.animation_counter
        self.animation_counter += 1
        name_suffix = f"attachable_hold_{index}"
        name, animation = attachable_hold_animation_template(
            name_suffix, position.as_list(), rotation.as_list(),
            scale.as_list())
        self.add_animation(name, animation)
        return name

    def add_animation(self, anim_name: str, data: dict):
        name_walker = self.walker / 'animations' / anim_name
        try:
            name_walker.create_path(
                data,
                can_break_data_structure=False,
                can_create_empty_list_items=False,
                exists_ok=False)
        except (ValueError, KeyError) as e:
            raise CustomBlocks2Error(dedent(f'''\
                Failed to add the animation.
                Path: {BpAnimationControllerJson.PATH.as_posix()}
                Animation: {anim_name}
                Error: {str(e)}'''))

class RpCubicAttachableAssets:
    '''
    A singleton that represents the file with the texture for the cubic
    attachables generated by this Regolith filter. It also generates the
    geometries, but only if textures are generated.
    '''
    TEXTURES_DIR_PATH = RP_PATH / Path("textures/attachable")
    '''The path to the directory where the textures should be stored.'''

    GEOMETRY_PATH = RP_PATH / Path("models/entity/cb2_cube.geo.json")
    '''The path to the geometry file for the cubic attachables.'''

    @staticmethod
    @cache
    def get() -> RpCubicAttachableAssets:
        return RpCubicAttachableAssets()

    @staticmethod
    def get_path_to_move_target(local_path: Path) -> Path:
        '''
        Maps the local paths to their target paths in the resource pack.
        '''
        return (
            RP_PATH / RpCubicAttachableAssets.TEXTURES_DIR_PATH / local_path)

    def save_if_not_empty(self):
        if RpCubicAttachableAssets.GEOMETRY_PATH.exists():
            raise CustomBlocks2Error(dedent(f'''\
                The geometry file for the cubic attachables already exists. '''
                f'''Please remove it and try again. Overriding this file is '''
                f'''not supported
                Path: {RpCubicAttachableAssets.GEOMETRY_PATH.as_posix()}'''))
        if self.texture_counter == 0:
            return
        geo_data = attachable_cube_geo()
        RpCubicAttachableAssets.GEOMETRY_PATH.parent.mkdir(
            exist_ok=True, parents=True)
        with RpCubicAttachableAssets.GEOMETRY_PATH.open('w', encoding='utf-8') as f:
            json.dump(geo_data, f, indent='\t', cls=CompactEncoder)

    def __init__(self):
        self.texture_counter = 0
        '''Used for generating unique identifiers for the textures.'''

    @cache
    def generate_and_save_cube_texture(
            self, sides: CubicAttachableTextureSides) -> Path:
        '''
        Creates a texture for a cubical attachable form 6 provided texture
        paths, saves it in the RP/texture/shapescape_custom_blocks_generator
        folder and returns the path to the texture (with PR/ included in the
        path).
        '''
        index = self.texture_counter
        self.texture_counter += 1
        north = sides.north
        south = sides.south
        east = sides.east
        west = sides.west
        up = sides.up
        down = sides.down

        new_img_path = self.TEXTURES_DIR_PATH / "cb2" / f"cube_{index}.png"
        if new_img_path.exists():
            raise CustomBlocks2Error(dedent(f'''\
                The texture for the cubic attachable already exists. Please '''
                f'''remove it and try again. Overriding this file is not '''
                f'''supported
                Path: {new_img_path.as_posix()}'''))
        def open_img(path: Path, name: str) -> Image.Image:
            try:
                return Image.open(path)
            except Exception as e:
                raise CustomBlocks2Error(dedent(f'''\
                    Failed to open the "{name}" texture for the block.
                    Path: {path.as_posix()}
                    Error: {str(e)}'''))
        n_img = (open_img(north, 'north'), north)
        s_img = (open_img(south, 'south'), south)
        e_img = (open_img(east, 'east'), east)
        w_img = (open_img(west, 'west'), west)
        up_img = (open_img(up, 'up'), up)
        down_img = (open_img(down, 'down'), down)
        expected_width, expected_height = n_img[0].width, n_img[0].height
        if expected_width != expected_height:
            raise CustomBlocks2Error(dedent(f'''\
                The width and height of the textures must be the same.
                Path: {north.as_posix()}'''))
        for img, img_path in [s_img, e_img, w_img, up_img, down_img]:
            if img.width != expected_width or img.height != expected_height:
                raise CustomBlocks2Error(dedent(f'''\
                    All of the textures in the cubic attachable must have '''
                    f'''the same width and height.
                    Path: {img_path.as_posix()}'''))
        new_img = Image.new(
            'RGBA', (expected_width * 4, expected_height*2))
        new_img.paste(w_img[0], (0, expected_height))
        new_img.paste(n_img[0], (expected_width, expected_height))
        new_img.paste(e_img[0], (expected_width*2, expected_height))
        new_img.paste(s_img[0], (expected_width*3, expected_height))
        new_img.paste(up_img[0], (expected_width, 0))
        new_img.paste(down_img[0], (expected_width*2, 0))

        new_img_path.parent.mkdir(parents=True, exist_ok=True)
        new_img.save(new_img_path)
        return new_img_path

class BlocksData:
    '''A class used to access the data from the _blocks_data.json file.'''

    def __init__(self, data_path: Path, scope: dict[str, Any]):
        self.scope: dict[str, Any] = scope
        self.data_path = data_path
        self.system_path = data_path.parent


        # Load the self.data file. Based on the file extension the process
        # differs.
        if self.data_path.suffix == '.json':
            try:
                data_walker = load_jsonc(data_path)
                with WdSwitch(self.system_path):
                    self.data = JSONWalker(
                        eval_json(data_walker.data, copy(self.scope)))
            except Exception as e:
                raise CustomBlocks2Error(dedent(f'''\
                    Failed to load the blocks data file.
                    Path: {self.data_path.as_posix()}
                    Error: {str(e)}'''))
        elif self.data_path.suffix == '.py':
            try:
                data_text = self.data_path.read_text(encoding='utf8')
                with WdSwitch(self.system_path):
                    evaluated_data = eval(data_text, copy(self.scope))
                # Check if the evaluated data is a valid JSON object
                _ = json.dumps(evaluated_data)  # We don't need the result
                self.data = JSONWalker(evaluated_data)
            except Exception as e:
                raise CustomBlocks2Error(
                    f"Failed to evaluate {self.data_path.as_posix()} the data "
                    "file. The data file must evaluate to a valid JSON "
                    "object.\n"
                    f"Error: {str(e)}")
        else:  # Shouldn't happen
            raise ValueError("The data path must be a .json or .py file.")

    @cached_property
    def blocks(self) -> tuple[_Block, ...]:
        '''
        A list of all the blocks in the _blocks_data.json file.
        '''
        blocks = self.data / 'blocks'
        if blocks.exists and not isinstance(blocks.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The 'blocks' property must be a dict.
                Path: {self.data_path.as_posix()}'''))
        return tuple(
            _Block(walker, self)
            for walker in blocks // str
        )

    @cached_property
    def namespace(self) -> str:
        '''
        The namespace of the pack.
        '''
        result: Any = (self.data / 'namespace').data
        if not isinstance(result, str):
            raise CustomBlocks2Error(dedent(f'''\
                The namespace property must be a string.
                Path: {self.data_path.as_posix()}'''))
        return result

    def generate(self) -> None:
        '''
        Generates everything based on this  _blocks_data.json file.
        '''
        for block in self.blocks:
            block.generate()
            RpBlocksJson.get().add_block(block)
            block.generate_recipes()

    def __str__(self) -> str:
        return dedent(f'''\
            BLOCKS DATA:
                Path: {self.data_path.as_posix()}
                Blocks:\n'''
        ) + "\n".join(
            indent(str(block), "    " * 2)
            for block in self.blocks
        )

class _Block:
    '''
    A class used to access the a block from the blocks property of the
    _blocks_data.json file.
    '''
    def __init__(self, walker: JSONWalker, parent: BlocksData):
        self.parent = parent
        self.walker = walker

    @cached_property
    def block_template(self) -> Path:
        '''
        The path to the template file relative to the _blocks_data.json file.
        '''
        blocks_data_path = self.parent.data_path.parent
        template_walker = self.walker / 'block_template'

        if not template_walker.exists:
            raise CustomBlocks2Error(dedent(f'''\
                The block template property is required.
                Path: {self.parent.data_path.as_posix()}
                JSON Path: {template_walker.path_str}'''))
        if not isinstance(template_walker.data, str):
            raise CustomBlocks2Error(dedent(f'''\
                The block template property must be a string.
                Path: {blocks_data_path}
                JSON Path: {template_walker.path_str}'''))
        return blocks_data_path / template_walker.data

    @cached_property
    def recipe_template(self) -> Path | None:
        '''
        The path to the template file with the recipe of the block relative
        to the _block_data.json file.
        '''
        blocks_data_path = self.parent.data_path.parent
        template_walker = self.walker / 'recipe_template'
        if not template_walker.exists:
            return None
        if not isinstance(template_walker.data, str):
            raise CustomBlocks2Error(dedent(f'''\
                The recipe template property must be a string.
                Path: {self.parent.data_path.as_posix()}
                JSON Path: {template_walker.path_str}'''))
        return blocks_data_path / template_walker.data

    @cached_property
    def translation(self) -> str | None:
        '''
        Returns the translation property for generating the translations for
        the en_US.lang file.
        '''
        translation_walker = self.walker / 'translation'
        if not translation_walker.exists:
            return None
        if not isinstance(translation_walker.data, str):
            raise CustomBlocks2Error(dedent(f'''\
                The translation property must be a string.
                Path: {self.parent.data_path.as_posix()}
                JSON Path: {translation_walker.path_str}'''))
        return translation_walker.data

    def get_evaluated_template(self) -> JSONWalker:
        '''
        Loads and evaluates the template file, and than returns it packed
        inside a JSONWalker of the template file.
        '''
        # GET THE FILE
        try:
            result = load_jsonc(self.block_template)
        except (JSONDecodeError, OSError) as e:
            raise CustomBlocks2Error(dedent(f'''\
                Failed to load the template file.
                Path: {self.block_template.as_posix()}
                Error: {str(e)}'''
            ))
        # EVALUATE THE FILE
        try:
            with WdSwitch(self.block_template.parent):
                result = JSONWalker(
                    eval_json(result.data, self.parent.scope))
        except Exception as e:
            raise CustomBlocks2Error(dedent(f'''\
                Failed to evaluate the template file.
                Path: {self.block_template.as_posix()}
                Error: {str(e)}'''
            )) from e

        # TRY TO ADD REQUIRED PROPERTIES
        # No guarantee that this will work but
        # it won't throw an error if it doesn't.

        # Try to make '['minecraft:block'].permutations' a list
        permutations_walker = result / 'minecraft:block' / 'permutations'
        try:
            permutations_walker.create_path(
                [], can_create_empty_list_items=False,
                can_break_data_structure=False,
                exists_ok=True)
        except (ValueError, KeyError):
            pass
        # Try to make ['minecraft:block']description.states a dict
        states_walker = (
            result / 'minecraft:block' / 'description' / 'states')
        try:
            states_walker.create_path(
                {}, can_create_empty_list_items=False,
                can_break_data_structure=False,
                exists_ok=True)
        except (ValueError, KeyError):
            pass
        # Return the result
        return result

    @cached_property
    def block_template_override(self) -> dict[str, Any] | None:
        '''
        Gets the block_template_override propert of the block. The result dict
        is wrapped in a 'minecraft:block' key for easier merging.
        '''
        custom_walker = self.walker / 'block_template_override'
        if not custom_walker.exists:
            return None
        if not isinstance(custom_walker.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The block_template_override property must be a dictionary.
                Path: {self.parent.data_path.parent}
                JSON Path: {custom_walker.path_str}'''
            ))
        return {"minecraft:block": custom_walker.data}

    @cached_property
    def recipe_template_override(self) -> dict[str, Any] | None:
        '''
        Gets the recipe_template_override property of the block. The result
        dict is used to be merged with the recipe template. It doesn't wrap
        the result in the 'minecraft:recipe_shaped',
        'minecraft:recipe_shapeless' etc. keys because they are unknown at
        this point.
        '''
        custom_walker = self.walker / 'recipe_template_override'
        if not custom_walker.exists:
            return None
        if not isinstance(custom_walker.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The recipe_template_override property must be a dictionary.
                Path: {self.parent.data_path.parent}
                JSON Path: {custom_walker.path_str}'''
            ))
        return custom_walker.data

    @cached_property
    def shared_variant(self) -> dict[str, Any]:
        '''
        The properties used in the permutations created from combining multiple
        permutations. These are the defaults that may be overriden by the
        actual permutations.
        '''
        shared_variant_walker = self.walker / 'shared_variant'
        if not shared_variant_walker.exists:
            return {}
        if not isinstance(shared_variant_walker.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The shared_variant property must be a dictionary.
                Path: {self.parent.data_path.parent}
                JSON Path: {shared_variant_walker.path_str}'''
            ))
        return shared_variant_walker.data

    @cached_property
    def variants(self) -> dict[str, list[_Variant]]:
        '''
        Returns all variant groups of the block.
        '''
        result: dict[str, list[_Variant]] = {}
        for variant_group in self.walker / 'variants' // str:
            # Build a list of all variants and make sure that their id_suffixes
            # are unique withing a variant group.
            result[variant_group.parent_key] = []
            id_suffixes: set[str] = set()
            variant_groups_walker = variant_group // int
            if not isinstance(variant_groups_walker.data, list):
                raise CustomBlocks2Error(dedent(f'''\
                    The variants property must be a list.
                    Path: {self.parent.data_path.as_posix()}
                    JSON Path: {variant_group.path_str}'''
                ))
            if len(variant_groups_walker.data) == 0:
                raise CustomBlocks2Error(dedent(f'''\
                    The variants property must not be empty.
                    Path: {self.parent.data_path.as_posix()}
                    JSON Path: {variant_group.path_str}'''
                ))
            for variant_obj in variant_group // int:
                if not isinstance(variant_obj.data, dict):
                    raise CustomBlocks2Error(dedent(f'''\
                        The variants property must be a dict.
                        Path: {self.parent.data_path.as_posix()}
                        JSON Path: {variant_obj.path_str}'''
                    ))
                variant_obj = _Variant(variant_obj, self)
                result[variant_group.parent_key].append(variant_obj)
                if variant_obj.id_suffix in id_suffixes:
                    raise CustomBlocks2Error(dedent(f'''\
                        The id_suffix "{variant_obj.id_suffix}" is used '''
                        f'''more than once in the variant group '''
                        f'''"{variant_group.parent_key}".
                        Path: {self.parent.data_path.as_posix()}
                        JSON Path: {variant_obj.walker.path_str}'''
                    ))
                if "_" in variant_obj.id_suffix:
                    raise CustomBlocks2Error(dedent(f'''\
                        The id_suffix "{variant_obj.id_suffix}" contains
                        underscores. This is not allowed.
                        Path: {self.parent.data_path.as_posix()}
                        JSON Path: {variant_obj.walker.path_str}'''
                    ))
        return result

    @cached_property
    def name(self) -> str:
        '''
        Returns the name of the block (without the namespace)
        '''
        return self.walker.parent_key

    @property
    def full_name(self) -> str:
        '''
        Returns the full name of the block with its namespace.
        '''
        return f'{self.parent.namespace}:{self.name}'

    @cached_property
    def sound(self) -> str:
        '''
        The sound property of the block.
        '''
        sound = self.walker / 'sound'
        if not isinstance(sound.data, str):
            raise CustomBlocks2Error(dedent(f'''\
                The sound property must be a string.
                Path: {self.parent.data_path.as_posix()}
                JSON Path: {sound.path_str}'''))
        return sound.data

    @cached_property
    def texture(self) -> str | None:
        '''
        The texture property of the block.
        '''
        texture = self.walker / 'texture'
        if not texture.exists:
            return None
        if not isinstance(texture.data, str):
            raise CustomBlocks2Error(dedent(f'''\
                The texture property must be a string.
                Path: {self.parent.data_path.as_posix()}
                JSON Path: {texture.path_str}'''))
        return texture.data

    @cached_property
    def self_drop(self) -> bool | None:
        '''
        The self_drop property of the block.
        '''
        self_drop = self.walker / 'self_drop'
        if not self_drop.exists:
            return None
        if not isinstance(self_drop.data, bool):
            raise CustomBlocks2Error(dedent(f'''\
                The self_drop property must be a boolean or undefined.
                Path: {self.parent.data_path.as_posix()}
                JSON Path: {self_drop.path_str}'''))
        return self_drop.data

    @cached_property
    def rotation_type(self) -> None | Literal[
            'align_front_xyz', 'align_front_xz', 'rotate_front_vertical', 'rotate_front_both',
            'align_top_xyz', 'align_top_xz', 'rotate_top_vertical', 'rotate_top_both']:
        '''
        The rotation_type property of the block.
        '''
        rotation_type = self.walker / 'rotation_type'
        if not rotation_type.exists:
            return None
        if rotation_type.data not in [
                'align_front_xyz', 'align_front_xz', 'rotate_front_vertical', 'rotate_front_both',
                'align_top_xyz', 'align_top_xz', 'rotate_top_vertical', 'rotate_top_both'
            ]:
            raise CustomBlocks2Error(dedent(f'''\
                The rotation_type property must be one of the following: '''
                '''align_front_xyz, align_front_xz, rotate_front_vertical, '''
                '''rotate_front_both, align_top_xyz, align_top_xz, '''
                '''rotate_top_vertical, rotate_top_both or '''
                f'''undefined.
                Path: {self.parent.data_path.as_posix()}
                JSON Path: {rotation_type.path_str}'''))
        return rotation_type.data

    @property
    def subdir(self) -> Path:
        '''
        A subdirectory for outputing the files based on the relation of the
        template to the self.parent.data_path.
        '''
        return self.block_template.parent.relative_to(self.parent.data_path.parent)

    def _walk_variants_cross_product(self) -> Iterator[_Variant]:
        '''
        Walks all variants of the block
        '''
        for v in product(*self.variants.values()):
            yield v

    def generate(self) -> None:
        # Load and evaluate the data using json_template
        result = self.get_evaluated_template()

        # Modify the result
        result = self._generate_overlay_custom_data(result)
        result = self._generate_add_identifier(result)
        result = self._generate_add_permutations_and_states(result)
        if self.rotation_type is None and len(self.variants) == 0:
            if self.self_drop:  # true, false or None (enters only if true)
                # If block has no variants and rotations it should handle
                # generating its own loot table, otherwise it's handled by
                # the _generate_add_block_entities function
                result = self._generate_add_loot_table(result)
                self.save_loot_file()
            # Add translation if it exists
            if self.translation:
                Lang.get().add(
                    f'tile.{self.full_name}.name',
                    f'{self.translation}')
        else:
            result = self._generate_add_rotations(result)
            for block_entity in self.block_entities:
                # Based on the rotation type or lack of rotation, generate
                # the AC and some variants of the block
                block_entity.generate()
                bp_ac = BpAnimationControllerJson.get()
                if self.rotation_type == None:
                    bp_ac.generate_no_rotation(block_entity)
                elif self.rotation_type in ['align_top_xyz', 'align_front_xyz']:
                    bp_ac.generate_align_xyz_bp_ac(block_entity)
                elif self.rotation_type in ['align_top_xz', 'align_front_xz']:
                    bp_ac.generate_align_xz_bp_ac(block_entity)
                elif self.rotation_type in ['rotate_top_vertical', 'rotate_front_vertical']:
                    bp_ac.generate_rotate_vertical_bp_ac(block_entity)
                elif self.rotation_type in ['rotate_top_both', 'rotate_front_both']:
                    bp_ac.generate_rotate_both_bp_ac(block_entity)
                # If self.self_drop is true, generate a variant with a
                # loot table to drop a right block entity.
                self._generate_add_shared_variants(result, block_entity)
                if self.self_drop or len(self.shared_variant) != 0:
                    block_entity.save_loot_file()

                # Add translation if it exists
                if self.translation:
                    translation = self.translation
                    for v in block_entity.variants:
                        if v.translation is not None:
                            translation = translation.replace(
                                f"{{{v.variant_name}}}",
                                v.translation)
                    Lang.get().add(
                        f'item.spawn_egg.entity.{block_entity.full_name}.name',
                        f'{translation}')
                    Lang.get().add(
                        f'entity.{block_entity.full_name}.name',
                        f'{translation}')
        # Save
        output_path = (
            Path("BP/blocks") / "cb2" / f'{self.name}.block.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf8') as f:
            json.dump(result.data, f, cls=CompactEncoder)

    def _generate_overlay_custom_data(self, result: JSONWalker) -> JSONWalker:
        '''
        A helper function for the generate() function. Overlays the custom data
        over the result of the generate function.
        '''
        custom_data = self.block_template_override
        if custom_data is not None:
            result = JSONWalker(
                deep_merge_objects(result.data, custom_data))
        return result

    def _generate_add_identifier(self, result: JSONWalker) -> JSONWalker:
        '''
        A helper function for the generate() function. Adds the identifier to
        the result of the generate function.
        '''
        name_path = (
            result / 'minecraft:block' / 'description' / 'identifier')
        name_value = f'{self.parent.namespace}:{self.name}'
        try:
            name_path.create_path(
                name_value,
                exists_ok=False,
                can_break_data_structure=False,
                can_create_empty_list_items=False
            )
        except (KeyError, ValueError) as e:
            raise CustomBlocks2Error(dedent(f'''\
                Failed to set the identifier of the block.
                The identifier of the block to generate: {name_value}
                Blocks data Path: {self.parent.data_path.as_posix()}
                Template Path: {self.block_template.as_posix()}
                JSON Path: {name_path.path_str}
                Error: {str(e)}'''))
        return result

    def _generate_add_permutations_and_states(
                self, result: JSONWalker) -> JSONWalker:
        '''
        A helper function for the generate() function. Adds the variants to the
        result of the generate function.
        '''
        # Helper variables. Acces certain parts of the JSON file
        permutations_walker = (
            result / 'minecraft:block' / 'permutations')
        if not isinstance(permutations_walker.data, list):
            raise CustomBlocks2Error(dedent(f'''\
                The permutations property must be a list.\n
                Path: {self.parent.data_path.as_posix()}
                JSON Path: {permutations_walker.path_str}'''))
        states_walker = (
            result / 'minecraft:block' / 'description' / 'states')
        if not isinstance(states_walker.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The 'states' property property must be a dict.
                Path: {self.parent.data_path.as_posix()}
                JSON Path: {states_walker.path_str}'''))
        for variant_k, variant in self.variants.items():
            # Add permutations and states related to them
            for i, v in enumerate(variant):
                property_name: str = f"{self.parent.namespace}:{variant_k}"
                permutations_walker.data.append({
                    "components": {} if v.components is None else v.components,
                    "condition": f"q.block_property('{property_name}') == {i}"
                })
                states_walker.data[property_name] = {
                    "values": {
                        "min": 0,
                        "max": len(variant) - 1,
                    }
                }
        return result

    def _generate_add_loot_table(self, result: JSONWalker) -> JSONWalker:
        loot_component = (
            result / 'minecraft:block' / 'components' / 'minecraft:loot')
        if loot_component.exists:
            raise CustomBlocks2Error(dedent(f'''\
                Can't add a 'self_drop' loot table beause the block already '''
                f'''has a loot component.
                Path: {self.parent.data_path.as_posix()}
                JSON Path: {loot_component.path_str}'''))
        loot_var = (
            Path('loot_tables') / 'cb2' / f'{self.name}.loot.json'
        ).as_posix()
        loot_component.create_path(loot_var)
        return result

    def _generate_add_shared_variants(
            self, result: JSONWalker, block_entity: _BlockEntity) -> None:
        '''
        A helper function for the generate() function. Adds extra permutations
        to the block. Every permutation drops a spawn egg of a block entity
        related to its configuration.
        '''
        permutations_walker = (
            result / 'minecraft:block' / 'permutations')
        if not isinstance(permutations_walker.data, list):
            raise CustomBlocks2Error(dedent(f'''\
                The permutations property must be a list.\n
                Path: {self.parent.data_path.as_posix()}
                JSON Path: {permutations_walker.path_str}'''))
        new_permutation: dict[str, Any] = {
            "condition": block_entity.molang_query,
            "components": {}
        }
        # If it's a self dropping entity, add a loot table
        if self.self_drop:
            loot_var = (
                Path('loot_tables') / 'cb2' /
                f'{block_entity.name}.loot.json'
            ).as_posix()
            new_permutation['components']['minecraft:loot'] = loot_var
        shared_variant = deepcopy(self.shared_variant)
        for variant in block_entity.variants:
            if len(variant.shared_variant) == 0:
                continue
            shared_variant: dict[str, Any] = deep_merge_objects(
                shared_variant, variant.shared_variant)
        new_permutation['components'] |= shared_variant

        # Add the new permutation
        permutations_walker.data.append(new_permutation)

    def _generate_add_rotations(self, result: JSONWalker) -> JSONWalker:
        '''
        A helper function for the generate() function. Adds the rotation type
        to the result of the generate function.
        '''
        # Generate rotation for this block (if it has it)
        if self.rotation_type == 'align_front_xyz':
            self._generate_align_front_xyz(result)
        elif self.rotation_type == 'align_front_xz':
            self._generate_align_front_xz(result)
        elif self.rotation_type == 'rotate_front_vertical':
            self._generate_rotate_front_vertical(result)
        elif self.rotation_type == 'rotate_front_both':
            self._generate_rotate_front_both(result)
        elif self.rotation_type == 'align_top_xyz':
            self._generate_align_top_xyz(result)
        elif self.rotation_type == 'align_top_xz':
            self._generate_align_top_xz(result)
        elif self.rotation_type == 'rotate_top_vertical':
            self._generate_rotate_top_vertical(result)
        elif self.rotation_type == 'rotate_top_both':
            self._generate_rotate_top_both(result)
        return result

    @cached_property
    def block_entities(self) -> list[_BlockEntity]:
        # Generate block entities
        block_entities: list[_BlockEntity]
        if len(self.variants) == 0:
            if self.rotation_type is None:
                block_entities = []
            else:
                block_entities = [_BlockEntity(self)]
        else:
            block_entities = [
                _BlockEntity(self, variants_group)
                for variants_group in self._walk_variants_cross_product()
            ]
        return block_entities

    def _generate_add_rotation_any(
            self, result: JSONWalker, permutations: list[dict],
            property: dict) -> None:
        # Get access to certain parts of the JSON file
        permutations_walker = (
            result / 'minecraft:block' / 'permutations')
        if not isinstance(permutations_walker.data, list):
            raise CustomBlocks2Error(dedent(f'''\
                The permutations property must be a list.\n
                Path: {self.parent.data_path.as_posix()}
                JSON Path: {permutations_walker.path_str}'''))
        states_walker = (
            result / 'minecraft:block' / 'description' / 'states')
        if not isinstance(states_walker.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The 'states' property property must be a dict.
                Path: {self.parent.data_path.as_posix()}
                JSON Path: {states_walker.path_str}'''))

        # Add permutations
        permutations_walker.data.extend(permutations)

        # Add property
        rotation_property_name = f"{self.parent.namespace}:rotation"
        rotation_walker = states_walker / rotation_property_name
        if rotation_walker.exists:
            raise CustomBlocks2Error(dedent(f'''\
                Can't add a {rotation_property_name} property beause the it '''
                f'''already exists.
                Path: {self.parent.data_path.as_posix()}
                JSON Path: {rotation_walker.path_str}'''))
        rotation_walker.create_path(property)

    def _generate_align_front_xyz(self, result: JSONWalker) -> tuple[dict, list[dict]]:
        property = {
            "values": {
                "min": 0,
                "max": 2
            }
        }
        permutations = [
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 0",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['xp_front']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 1",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['yp_front']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 2",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['zp_front']
                    }
                }
            }
        ]
        self._generate_add_rotation_any(result, permutations, property)

    def _generate_align_front_xz(self, result: JSONWalker) -> tuple[dict, list[dict]]:
        property = {
            "values": {
                "min": 0,
                "max": 1
            }
        }
        permutations = [
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 0",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['xp_front']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 1",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['zp_front']
                    }
                }
            }
        ]
        self._generate_add_rotation_any(result, permutations, property)

    def _generate_rotate_front_vertical(self, result: JSONWalker) -> tuple[dict, list[dict]]:
        property = {
            "values": {
                "min": 0,
                "max": 3
            }
        }
        permutations = [
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 0",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['xp_front']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 1",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['xm_front']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 2",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['zp_front']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 3",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['zm_front']
                    }
                }
            },
        ]
        self._generate_add_rotation_any(result, permutations, property)

    def _generate_rotate_front_both(
            self, result: JSONWalker) -> tuple[dict, list[dict]]:
        property = {
            "values": {
                "min": 0,
                "max": 5
            }
        }
        permutations = [
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 0",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['xp_front']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 1",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['xm_front']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 2",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['yp_front']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 3",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['ym_front']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 4",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['zp_front']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 5",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['zm_front']
                    }
                }
            },
        ]
        self._generate_add_rotation_any(result, permutations, property)

    def _generate_align_top_xyz(self, result: JSONWalker) -> tuple[dict, list[dict]]:
        property = {
            "values": {
                "min": 0,
                "max": 2
            }
        }
        permutations = [
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 0",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['xp_top']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 1",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['yp_top']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 2",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['zp_top']
                    }
                }
            }
        ]
        self._generate_add_rotation_any(result, permutations, property)

    def _generate_align_top_xz(self, result: JSONWalker) -> tuple[dict, list[dict]]:
        property = {
            "values": {
                "min": 0,
                "max": 1
            }
        }
        permutations = [
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 0",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['xp_top']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 1",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['zp_top']
                    }
                }
            }
        ]
        self._generate_add_rotation_any(result, permutations, property)

    def _generate_rotate_top_vertical(self, result: JSONWalker) -> tuple[dict, list[dict]]:
        property = {
            "values": {
                "min": 0,
                "max": 3
            }
        }
        permutations = [
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 0",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['xp_top']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 1",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['xm_top']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 2",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['zp_top']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 3",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['zm_top']
                    }
                }
            },
        ]
        self._generate_add_rotation_any(result, permutations, property)

    def _generate_rotate_top_both(
            self, result: JSONWalker) -> tuple[dict, list[dict]]:
        property = {
            "values": {
                "min": 0,
                "max": 5
            }
        }
        permutations = [
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 0",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['xp_top']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 1",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['xm_top']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 2",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['yp_top']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 3",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['ym_top']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 4",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['zp_top']
                    }
                }
            },
            {
                "condition": f"q.block_property('{self.parent.namespace}:rotation') == 5",
                "components": {
                    "minecraft:transformation": {
                        "rotation": BLOCK_ROTATION_TRANSFORMATION_MAP['zm_top']
                    }
                }
            },
        ]
        self._generate_add_rotation_any(result, permutations, property)

    def save_loot_file(self) -> None:
        '''
        Saves the loot table file for self dropping of the block. Assumes
        that the self.self_drop is True.
        '''
        data = self_drop_loot_table_template(
            f"{self.parent.namespace}:{self.name}")
        output_path: Path = (
            Path("BP/loot_tables") / 'cb2' / f'{self.name}.loot.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf8') as f:
            json.dump(data, f, cls=CompactEncoder)

    def generate_recipes(self) -> None:
        '''
        Generates the recipes for the block.
        '''
        if self.recipe_template is None:
            return
        if len(self.block_entities) == 0:
            recipes = [_Recipe(self)]
        else:
            recipes = [
                _Recipe(self, block_entity)
                for block_entity in self.block_entities
            ]
        for recipe in recipes:
            recipe.generate()

    def __str__(self) -> str:
        return dedent(f'''\
            Block:
                Template: {self.block_template.as_posix()}
                Variants:\n'''
        ) + "\n".join(
            indent(k, "    " * 2)
            for k in self.variants.keys()
        )

class _Recipe:
    '''
    A class used to generate the recipe for a block.
    '''
    RECIPE_COUNTER = defaultdict(int)

    def __init__(
            self, parent: _Block, block_entity: _BlockEntity | None = None):
        self.parent = parent
        if self.parent.recipe_template is None:
            raise CustomBlocks2Error(dedent(f'''\
                The recipe_template of the block must be set in order '''
                f'''to generate the recipe.
                _blocks_data.json path: {self.parent.parent.data_path.as_posix()}
                Block: {self.parent.walker.path_str}'''))
        self.block_entity = block_entity

    def next_recipe_suffix(self) -> str:
        '''
        Returns a suffix added to the name of the recipe to make it unique.
        It's based on the name of the block. If the name hasn't been used yet,
        it will return an empty string.
        '''
        k = (
            self.parent.name
            if self.block_entity is None else
            self.block_entity.name)
        result = _Recipe.RECIPE_COUNTER[k]
        _Recipe.RECIPE_COUNTER[k] += 1
        if result == 0:
            return ""
        return f'_{result}'

    @cached_property
    def name(self) -> str:
        '''
        The name of the recipe.
        '''
        if self.block_entity is None:
            return f"{self.parent.name}{self.next_recipe_suffix()}"
        return f"{self.block_entity.name}{self.next_recipe_suffix()}"

    @cached_property
    def full_name(self) -> str:
        return f"{self.parent.parent.namespace}:{self.name}"

    @cached_property
    def recipe_result(self) -> str:
        '''
        The result of the recipe inserted into output/result field in the
        generated file.
        '''
        if self.block_entity is None:
            return self.parent.full_name
        return f"{self.block_entity.full_name}_spawn_egg"

    def get_evaluated_template(self) -> JSONWalker:
        '''
        Loads and evaluates the recipe template file, and than returns it
        packed inside a JSONWalker of the template file.
        '''
        # GET THE FILE
        try:
            result = load_jsonc(self.parent.recipe_template)
        except (JSONDecodeError, OSError) as e:
            raise CustomBlocks2Error(dedent(f'''\
                Failed to load the template file.
                Path: {self.parent.recipe_template.as_posix()}
                Error: {str(e)}'''
            ))

        # EVALUATE THE FILE
        try:
            with WdSwitch(self.parent.recipe_template.parent):
                result = JSONWalker(
                    eval_json(result.data, self.parent.parent.scope))
        except Exception as e:
            raise CustomBlocks2Error(dedent(f'''\
                Failed to evaluate the template file.
                Path: {self.parent.recipe_template.as_posix()}
                Error: {str(e)}'''
            )) from e

        # Return the result
        return result

    def generate(self) -> None:
        '''
        Generates and saves the recipe.
        '''
        # Load and evaluate the template file
        result = self.get_evaluated_template()
        if not isinstance(result.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The recipe template must be a dictionary.
                Path: {self.parent.recipe_template.as_posix()}'''))

        # Modify the result core (in place)
        result_core = self._generate_get_result_core(result)
        self._generate_insert_custom_data_to_result_core(result_core)
        self._generate_insert_identifier_and_result_to_result_core(result_core)

        # Save the result
        output_path = (
            Path("BP/recipes") / 'cb2' /
            f"{self.name}.recipe.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', encoding='utf8') as f:
            json.dump(result.data, f, cls=CompactEncoder)

    def _generate_get_result_core(self, result: JSONWalker) -> JSONWalker:
        '''
        Returns the inner part of the JSON file with the recipe, that
        actually contains the recipe data.
        '''
        # Get the core of the recipe_template (the type of the recipe)
        if 'minecraft:recipe_shaped' in result.data:
            result_core = result / 'minecraft:recipe_shaped'
        elif 'minecraft:recipe_shapeless' in result.data:
            result_core = result / 'minecraft:recipe_shapeless'
        elif 'minecraft:recipe_furnace' in result.data:
            result_core = result / 'minecraft:recipe_furnace'
        elif 'minecraft:recipe_brewing_mix' in result.data:
            result_core = result / 'minecraft:recipe_brewing_mix'
        else:
            raise CustomBlocks2Error(dedent(f'''\
                Unknown recipe type. The recipe type must be one of the'''
                f'''following:
                - minecraft:recipe_shaped
                - minecraft:recipe_shapeless
                - minecraft:recipe_furnace
                - minecraft:recipe_brewing_mix
                Recipe template path: {self.parent.recipe_template.as_posix()}
                _block_data.json path: {self.parent.parent.data_path.as_posix()}
                Block JSON path: {self.parent.walker.path_str}'''
            ))
        return result_core

    def _generate_insert_custom_data_to_result_core(
            self, result_core: JSONWalker):
        '''
        Overlay the custom data onto the recipe. This function works in place.
        '''
        # Get custom data
        custom_data = self.parent.recipe_template_override
        if custom_data is not None:
            # Overlay the custom data
            result_core.data = deep_merge_objects(
                result_core.data,
                deepcopy(custom_data))

        if self.block_entity is not None:
            for v in self.block_entity.variants:
                if v.recipe is None:
                    continue
                # Overlay the custom data
                result_core.data = deep_merge_objects(
                    result_core.data,
                    deepcopy(v.recipe))

    def _generate_insert_identifier_and_result_to_result_core(
            self, result_core: JSONWalker):
        # Create the identifier
        identifier_walker = result_core / 'description' / 'identifier'
        try:
            identifier_walker.create_path(
                self.full_name,
                can_break_data_structure=False,
                can_create_empty_list_items=False,
                exists_ok=False
            )
        except (KeyError, ValueError) as e:
            raise CustomBlocks2Error(dedent(f'''\
                Failed to create an identifier for the recipe.
                Recipe template path: {self.parent.recipe_template.as_posix()}
                Identifier JSON path: {identifier_walker.path_str}
                _block_data.json path: {self.parent.parent.data_path.as_posix()}
                Block JSON path: {self.parent.walker.path_str}
                Error: {str(e)}'''))
        # Create the result
        if result_core.parent_key in (
                'minecraft:recipe_furnace', 'minecraft:recipe_brewing_mix'):
            result_path = result_core / 'output'
        elif result_core.parent_key in (
                'minecraft:recipe_shaped', 'minecraft:recipe_shapeless'):
            result_path = result_core / 'result' / "item"
        else:
            raise ValueError(  # Should never happen
                f"Unknown recipe type {result_core.parent_key}")
        try:
            result_path.create_path(
                self.recipe_result,
                exists_ok=False,
                can_break_data_structure=False,
                can_create_empty_list_items=False,
            )
        except (KeyError, ValueError) as e:
            raise CustomBlocks2Error(dedent(f'''\
                Failed to create a result for the recipe.
                Recipe template path: {self.parent.recipe_template.as_posix()}
                Result JSON path: {result_path.path_str}
                _block_data.json path: {self.parent.parent.data_path.as_posix()}
                Block JSON path: {self.parent.walker.path_str}
                Error: {str(e)}'''))

class _BlockEntity:
    '''
    A class used for generating the blocks entiteis used for spawning
    rotational blocks.
    '''
    def __init__(self, parent: _Block, variants: tuple[_Variant, ...]=tuple()):
        self.parent = parent
        self.variants = variants

    @cached_property
    def _name_suffix(self) -> str:
        '''
        A suffix added to various names of this block entity based on
        the variants of the block provided to this entity.
        '''
        if len(self.variants) == 0:
            return ''
        return '_' + "_".join(
            variant.id_suffix
            for variant in self.variants
        )

    @property
    def name(self) -> str:
        '''
        The name of the block entity based on its related block and variants
        of the block provided to this entity.
        '''
        return f"{self.parent.name}{self._name_suffix}"

    @property
    def full_name(self) -> str:
        '''
        Returns a full name of an entity with its namespace.
        '''
        return f"{self.parent.parent.namespace}:{self.name}"
    @property
    def spawn_egg_name(self) -> str:
        '''
        The name of the spawn egg for this block entity.
        '''
        return f"{self.name}_spawn_egg"

    @property
    def spawn_egg_full_name(self) -> str:
        '''
        The name of the spawn egg for this block entity.
        '''
        return f"{self.full_name}_spawn_egg"

    @cached_property
    def place_sound(self) -> str:
        sound = (
            self.parent.walker / 'block_entity_properties' / 'place_sound')
        if sound.exists:
            if not isinstance(sound.data, str):
                raise CustomBlocks2Error(dedent(f'''\
                    The place sound must be a string.
                    Path: {self.parent.parent.data_path.as_posix()}
                    JSON Path: {sound.path_str}'''))
            return sound.data
        return f"use.{self.parent.sound}"

    @cached_property
    def spawn_egg_texture(self) -> str | None:
        spawn_egg_texture_walker = (
            self.parent.walker / 'block_entity_properties' /
            'spawn_egg_texture')
        if spawn_egg_texture_walker.exists:
            if not isinstance(spawn_egg_texture_walker.data, str):
                raise CustomBlocks2Error(dedent(f'''\
                    The spawn egg texture must be a string.
                    Path: {self.parent.parent.data_path.as_posix()}
                    JSON Path: {spawn_egg_texture_walker.path_str}'''))
            return (
                f"{spawn_egg_texture_walker.data}{self._name_suffix}")
        return None

    @cached_property
    def attachable(self) -> _Attachable | None:
        '''
        Optional attachable used to display the item in the player's hand.
        '''
        attachable_walkers = []
        # Get the default attachable settings from the parent
        default_attachable_walker = (
            self.parent.walker / 'block_entity_properties' / 'attachable')
        if default_attachable_walker.exists:
            attachable_walkers.append(default_attachable_walker)
        for variant in self.variants:
            variant_attachable_walker = (
                variant.walker / 'block_entity_properties' / 'attachable')
            if variant_attachable_walker.exists:
                attachable_walkers.append(variant_attachable_walker)
        for aw in attachable_walkers:
            if not isinstance(aw.data, dict):
                raise CustomBlocks2Error(dedent(f'''\
                    The attachable property must be a dictionary.
                    Path: {self.parent.parent.data_path.as_posix()}
                    JSON Path: {aw.path_str}'''))
        if len(attachable_walkers) == 0:
            return None
        return _Attachable(attachable_walkers, self)

    @cached_property
    def block_data_items(self) -> str:
        '''
        Returns a string of all variant definitions for the block data in
        the setblock command.

        Example:
        "shapescape:material":1,"shapescape:color":2

        This represents a block entity that spawns a block with material 1 and
        color 2.
        '''
        return ",".join(
            variant.block_data_item
            for variant in self.variants
        )

    @cached_property
    def molang_query(self) -> str:
        '''
        Returns a molang query that tests for the combination of variants for
        this block entity.
        '''
        if len(self.variants) > 0:
            return ' && '.join(
                variant.molang_query
                for variant in self.variants
            )
        return "1.0"

    @cached_property
    def entity_override(self) -> dict:
        '''
        The dictionary merged with the block entity behavior
        '''
        walker = self.parent.walker / 'block_entity_properties' / 'entity_override'
        if not walker.exists:
            return {}
        if not isinstance(walker.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The entity_override property must be a dictionary.
                Path: {self.parent.parent.data_path.as_posix()}
                JSON Path: {walker.path_str}'''))
        # Check for properties that are not allowed to be overriden
        descriptoin_walker = walker / 'description'
        for k in (
                'identifier', 'is_experimental', 'is_spawnable',
                'is_summonable', 'animations', 'scripts'):
            property_walker = descriptoin_walker / k
            if property_walker.exists:
                raise CustomBlocks2Error(dedent(f'''\
                    The entity_override property cannot override the '''
                    f'''"{k}" property in the "description".
                    Path: {self.parent.parent.data_path.as_posix()}
                    JSON Path: {property_walker.path_str}'''))
        return walker.data

    def get_block_data_items_with_rotation(self, rotation: int):
        '''
        Returns self.block_data_items with an additional rotation value.
        '''
        if len(self.variants) == 0:  # self.block_data_items --> ""
            return f'"{self.parent.parent.namespace}:rotation"={rotation}'
        return ",".join([
            self.block_data_items,
            f'"{self.parent.parent.namespace}:rotation"={rotation}'
        ])

    def generate(self) -> None:
        '''
        Generates the block entity for the block and all of its files.
        '''
        # Generate BP entity
        bp_data = block_entity_behavior_template(
            self.parent.parent.namespace, self.name)
        output_path: Path = (
            Path("BP/entities") / "cb2" /
            f'{self.name}.behavior.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            raise CustomBlocks2Error(dedent(f'''\
                The block entity file already exists.
                Path: {output_path.as_posix()}'''))
        # Merge with the minecraft:entity properties
        bp_data['minecraft:entity'] = deep_merge_objects(
            bp_data['minecraft:entity'],
            self.entity_override)
        with output_path.open('w', encoding='utf8') as f:
            json.dump(bp_data, f, cls=CompactEncoder)

        # Generate RP entity, if the texture is defined
        if self.spawn_egg_texture is not None:
            block_entity_data = block_entity_entity_template(
                self.parent.parent.namespace, self.name,
                self.spawn_egg_texture)
            output_path: Path = (
                Path("RP/entity/cb2") / self.parent.subdir /
                f'{self.name}.entity.json')
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open('w', encoding='utf8') as f:
                json.dump(block_entity_data, f, cls=CompactEncoder)
        else:
            print_yellow(dedent(f'''
                Warning: The spawn_egg_texture is not defined for at '''
                f''' least one block entity.
                Block entity: {self.full_name}
                Path: {self.parent.parent.data_path.as_posix()}
                Block: {self.parent.walker.path_str}"'''))
        # Generate the attachable only if it's defined
        if self.attachable is not None:
            if self.attachable.is_cubic_attachable:
                geometry = ATTACHABLE_CUBE_GEO_ID
                if not isinstance(
                        self.attachable.texture, CubicAttachableTextureSides):
                    # This error is actually correct. From the user's
                    # perspective the 'texture' property is a dictionary.
                    raise CustomBlocks2Error(dedent(f'''\
                        The texture property for generated attachable '''
                        f'''textures must be a dictionary.
                        Path: {self.parent.parent.data_path.as_posix()}
                        JSON Path: {self.parent.walker.path_str}'''))
                rp_attachables = RpCubicAttachableAssets.get()
                texture = rp_attachables.generate_and_save_cube_texture(
                        self.attachable.texture)
            else:
                geometry = self.attachable.geometry
                if not isinstance(self.attachable.texture, Path):
                    raise CustomBlocks2Error(dedent(f'''\
                        The texture property of the attachable that '''
                        f'''is not cubic (generated) attachable must be a '''
                        f'''string with a path to the texture.
                        Path: {self.parent.parent.data_path.as_posix()}
                        JSON Path: {self.parent.walker.path_str}'''))
                texture = self.attachable.texture
            # CREATE THE HOLDING ANIMATION FOR THE ATTACHABLE
            attachable_anim_generator = RpAttachableAnimationJson.get()
            first_person_anim_name = (
                attachable_anim_generator.generate_hold_animation(
                    position=self.attachable.position_1st_person,
                    rotation=self.attachable.rotation_1st_person,
                    scale=self.attachable.scale_1st_person
                ))
            third_person_anim_name = (
                attachable_anim_generator.generate_hold_animation(
                    position=self.attachable.position_3rd_person,
                    rotation=self.attachable.rotation_3rd_person,
                    scale=self.attachable.scale_3rd_person
                ))
            # CREATE THE ATTACHABLE
            attachable_data = attachable_template(
                full_name=self.spawn_egg_full_name,
                geometry=geometry,
                texture=texture.relative_to(RP_PATH).with_suffix("").as_posix(),
                first_person_anim=first_person_anim_name,
                third_person_anim=third_person_anim_name,
                material="entity_alphatest"
            )
            output_path = (
                Path("RP/attachables") / "cb2" /
                f"{self.spawn_egg_name}.attachable.json")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with output_path.open('w', encoding='utf8') as f:
                json.dump(attachable_data, f, cls=CompactEncoder)

    def save_loot_file(self) -> None:
        '''
        Saves the loot table file for self dropping of the spawn egg of the
        block entity. Assumes that the self.self_drop is True.
        '''
        data = self_drop_loot_table_template(f"{self.full_name}_spawn_egg")
        output_path: Path = (
            Path("BP/loot_tables") / 'cb2' /
            f'{self.name}.loot.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf8') as f:
            json.dump(data, f, cls=CompactEncoder)

class _Variant:
    '''A class used to access a variant of a block.'''
    def __init__(self, walker: JSONWalker, parent: _Block):
        self.parent = parent
        self.walker = walker

    @cached_property
    def shared_variant(self) -> dict[str, Any]:
        '''
        Returns the shared variant data for this variant.
        '''
        shared_variant_walker = self.walker / 'shared_variant'
        if not shared_variant_walker.exists:
            return {}
        if not isinstance(shared_variant_walker.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The shared_variant property must be a dictionary.
                Path: {self.parent.data_path.parent}
                JSON Path: {shared_variant_walker.path_str}'''))
        return shared_variant_walker.data

    @cached_property
    def index(self) -> str:
        '''
        An identifier of the variant inside its variant group.
        The identifier is based on the index of the variant in its group list.
        '''
        return str(self.walker.parent_key)

    @cached_property
    def id_suffix(self) -> str:
        '''
        Returns the suffix for generating the name of the variant (for example,
        for the name of the block entity). Defaults to the self.index but can
        be overriden by the user.
        '''
        id_suffix_walker = self.walker / 'id_suffix'
        if not id_suffix_walker.exists:
            return self.index
        if not isinstance(id_suffix_walker.data, str):
            raise CustomBlocks2Error(dedent(f'''\
                The id_suffix property must be a string.
                Path: {self.parent.data_path.parent}
                JSON Path: {id_suffix_walker.path_str}'''))
        return id_suffix_walker.data


    @property
    def variant_name(self) -> str:
        return self.walker.parent.parent_key

    @cached_property
    def property_name(self):
        return (
            f'{self.parent.parent.namespace}:{self.walker.parent.parent_key}')

    @property
    def block_data_item(self) -> str:
        '''
        Returns an argument for defining the block data in the setblock command
        for this variant.

        Example:
        "shapescape:material":1

        If this variant represents the material, the namespace is shapescape,
        and value is 1.
        '''
        return f'"{self.property_name}"={self.index}'

    @cached_property
    def components(self) -> dict[str, Any] | None:
        '''
        Returns the components of the variant.
        '''
        components_walker = self.walker / 'components'
        if not components_walker.exists:
            return None
        if not isinstance(components_walker.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The components property must be a dictionary.
                Path: {self.parent.parent.data_path.parent}
                JSON Path: {components_walker.path_str}'''))
        return components_walker.data

    @cached_property
    def molang_query(self) -> str:
        '''
        Returns a molang query to test for this variant.
        '''
        return f"q.block_property('{self.property_name}') == {self.index}"

    @cached_property
    def recipe(self) -> dict[str, Any] | None:
        '''
        Returns the recipe to overlay over the block recipe for this variant.
        '''
        recipe_walker = self.walker / 'recipe'
        if not recipe_walker.exists:
            return None
        if not isinstance(recipe_walker.data, dict):
            raise CustomBlocks2Error(dedent(f'''\
                The recipe property must be a dictionary.
                Path: {self.parent.parent.data_path.as_posix()}
                JSON Path: {recipe_walker.path_str}'''))
        return recipe_walker.data

    @cached_property
    def translation(self) -> str | None:
        translation_walker = self.walker / 'translation'
        if not translation_walker.exists:
            return None
        if not isinstance(translation_walker.data, str):
            raise CustomBlocks2Error(dedent(f'''\
                The translation property must be a string.
                Path: {self.parent.parent.data_path.as_posix()}
                JSON Path: {translation_walker.path_str}'''))
        return translation_walker.data

    def __str__(self) -> str:
        return dedent(f'''\
            Variant:
                Components: {self.components}
            ''')

class _Attachable:
    '''
    A class used to access the attachable property of a block entity.
    Attachables are based on the default value defined in the block, and
    can be overriden by the variants that belong to the block entity.
    '''

    def __init__(self, walkers: list[JSONWalker], parent: _BlockEntity):
        '''
        :param walkers: A list of JSONWalkers to contribute to the settings
            of the attachable. It's the 'attachable' property of the blokc
            and the variatns of the block entity.
        '''
        self.parent = parent
        if len(walkers) == 0:
            # Should never happen
            raise ValueError(
                "Trying to create an attachable without any data.")
        self.walkers = walkers

    def _get_specific_offset(
            self, *,
            key: str,
            property_name: str,
            default_value: tuple[float, float, float]) -> MolangVector3D:
        '''
        Used for returning position, rotation and scale of the attachable
        in 1st and 3rd preson.
        '''
        # Walk in reverse because the last one is the most important
        for walker in reversed(self.walkers):
            position = walker / 'offset' / key
            if position.exists:
                try:
                    return MolangVector3D.new(position.data)
                except CustomBlocks2Error as e:
                    raise CustomBlocks2Error(dedent(f'''\
                        Failed to parse the {property_name} of the attachable.
                        Path: {self.parent.parent.parent.data_path.as_posix()}
                        JSON Path: {position.path_str}
                        Error: {str(e)}''')) from e
        return MolangVector3D(
            default_value[0], default_value[1], default_value[2])

    @cached_property
    def position_1st_person(self) -> MolangVector3D:
        '''
        Returns the position of the attachable in 1st person.
        '''
        # Walk in reverse because the last one is the most important
        return self._get_specific_offset(
            key='position_1st_person',
            property_name='position',
            default_value=ATTACHABLE_HOLD_1ST_PERSON_POSITION)

    @cached_property
    def rotation_1st_person(self) -> MolangVector3D:
        '''
        Returns the rotation of the attachable in 1st person.
        '''
        # Walk in reverse because the last one is the most important
        return self._get_specific_offset(
            key='rotation_1st_person',
            property_name='rotation',
            default_value=ATTACHABLE_HOLD_1ST_PERSON_ROTATION)

    @cached_property
    def scale_1st_person(self) -> MolangVector3D:
        '''
        Returns the scale of the attachable in 1st person.
        '''
        return self._get_specific_offset(
            key='scale_1st_person',
            property_name='scale',
            default_value=ATTACHABLE_HOLD_1ST_PERSON_SCALE)

    @cached_property
    def position_3rd_person(self) -> MolangVector3D:
        '''
        Returns the position of the attachable in 3rd person.
        '''
        return self._get_specific_offset(
            key='position_3rd_person',
            property_name='position',
            default_value=ATTACHABLE_HOLD_3RD_PERSON_POSITION)

    @cached_property
    def rotation_3rd_person(self) -> MolangVector3D:
        '''
        Returns the rotation of the attachable in 3rd person.
        '''
        return self._get_specific_offset(
            key='rotation_3rd_person',
            property_name='rotation',
            default_value=ATTACHABLE_HOLD_3RD_PERSON_ROTATION)

    @cached_property
    def scale_3rd_person(self) -> MolangVector3D:
        '''
        Returns the scale of the attachable in 3rd person.
        '''
        return self._get_specific_offset(
            key='scale_3rd_person',
            property_name='scale',
            default_value=ATTACHABLE_HOLD_3RD_PERSON_SCALE)

    @cached_property
    def geometry(self) -> str:
        '''
        Returns the identifier of the geometry to be used by the attachable.
        '''
        for walker in reversed(self.walkers):
            geometry = walker / 'assets' / 'geometry'
            if geometry.exists:
                if not isinstance(geometry.data, str):
                    raise CustomBlocks2Error(dedent(f'''\
                        The geometry property must be a string.
                        Path: {self.parent.parent.parent.data_path.as_posix()}
                        JSON Path: {geometry.path_str}'''))
                return geometry.data
        raise CustomBlocks2Error(dedent(f'''
            Missing geometry property for the attachable.
            Path: {self.parent.parent.parent.data_path.as_posix()}
            JSON Path: {geometry.path_str}'''))

    @property
    def is_cubic_attachable(self):
        '''
        Returns True if the attachable needs to generate a geometry and texture
        for the block.
        '''
        return isinstance(self.texture, CubicAttachableTextureSides)

    @cached_property
    def texture(self) -> Path | CubicAttachableTextureSides:
        '''
        Returns the value of the texture property with resolved paths.
        The paths are always starting from the RP root (root is included).
        '''
        # LOAD SOME DITE
        top_walker = self.walkers[-1]
        texture = top_walker / 'assets' / 'texture'
        system_dir_path = self.parent.parent.parent.data_path.parent

        # CLOSURE FOR RESOLVING PATHS TO THE ACTUAL PATH OBJECTS
        def _resolve_path(path_id: str):
            if path_id.startswith("TERRAIN_TEXTURE:"):
                try:
                    # Identifier in RP is a path relative to RP/ without
                    # the extension
                    result_path_rp_identifier = (
                        TerrainTexture.get()
                        .get_texture_path_identifier(
                            path_id.lstrip("TERRAIN_TEXTURE:")))
                except CustomBlocks2Error as e:
                    raise CustomBlocks2Error(dedent(f'''\
                        Failed to get the texture path for the attachable.
                        _blocks_data.json path: {system_dir_path.as_posix()}
                        Texture identifier: {path_id}

                        Loading failed due to the following error:

                        ''') +
                        str(e)
                    ) from e
                # TODO - maybe add support for other kinds of extensions than
                # .png?
                result_path = RP_PATH / f'{result_path_rp_identifier}.png'
            elif path_id.startswith("RP:"):
                result_path = RP_PATH / f'{path_id.lstrip("RP:")}.png'
            else:
                raise CustomBlocks2Error(
                    'The texture path must start with either with '
                    '"TERRAIN_TEXTURE:" or "RP:".\n'
                    '- Use "RP:" for textures relative to the '
                    'resource pack root (RP/).\n'
                    '- Use "TERRAIN_TEXTURE:" for textures defined in the '
                    '  terrain_texture.json file of the resource pack.'
                )
            if not result_path.exists():
                raise CustomBlocks2Error(dedent(f'''\
                    The texture file of the attachable doesn't exist.
                    _blocks_data.json path: {system_dir_path.as_posix()}
                    Texture path: {result_path.as_posix()}'''))
            return result_path

        # THE MAIN FUNCTION BODY
        if isinstance(texture.data, str):
            return _resolve_path(texture.data)
        result_dict: dict[str, Path] = {}
        sides = ["north", "south", "east", "west", "up", "down"]
        for walker in self.walkers:
            texture = walker / 'assets' / 'texture'
            if texture.exists:
                if isinstance(texture.data, str):
                    continue
                if not isinstance(texture.data, dict):
                    raise CustomBlocks2Error(dedent(f'''\
                        The texture property must be a string or a dictionary.
                        Path: {self.parent.parent.parent.data_path.as_posix()}
                        JSON Path: {texture.path_str}'''))
                for side in sides:
                    if side in texture.data:
                        side_val = texture.data[side]
                        if not isinstance(side_val, str):
                            raise CustomBlocks2Error(dedent(f'''\
                                The texture for side "{side}" must be a string.
                                Path: {self.parent.parent.parent.data_path.as_posix()}
                                JSON Path: {texture.path_str}'''))
                        result_dict[side] = _resolve_path(side_val)
        try:
            return CubicAttachableTextureSides(**result_dict)
        except TypeError as e:
            raise CustomBlocks2Error(dedent(f'''\
                Failed to parse the texture property of the attachable.
                Path: {self.parent.parent.parent.data_path.as_posix()}
                JSON Path: {texture.path_str}
                Error: {str(e)}''')) from e
