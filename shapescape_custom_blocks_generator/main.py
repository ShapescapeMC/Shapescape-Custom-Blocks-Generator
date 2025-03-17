from __future__ import annotations

import math
import sys
import uuid
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Iterator
import os

import json
from better_json_tools import load_jsonc
from better_json_tools.json_walker import JSONWalker
from blocks_data import (
    BlocksData, RpBlocksJson, BpAnimationControllerJson, Lang,
    RpAttachableAnimationJson, RpCubicAttachableAssets)
from errors import CustomBlocks2Error, print_red


DATA_PATH = Path('data')
FILTER_DATA_DIR = DATA_PATH / Path("shapescape_custom_blocks_generator")

def yield_block_data_files(scope: dict[str, Any]) -> Iterator[BlocksData]:
    '''
    Loads the 'data.json' file.
    '''
    for dir_path in FILTER_DATA_DIR.glob("*/**"):
        if not dir_path.is_dir():
            continue
        local_scope_path = dir_path / "_scope.json"
        if not local_scope_path.exists() or local_scope_path.is_dir():
            continue
        blocks_data_json_path = dir_path / "_blocks_data.json"
        blocks_data_py_path = dir_path / "_blocks_data.py"
        bdj_ok = blocks_data_json_path.exists() and not blocks_data_json_path.is_dir()
        bdp_ok = blocks_data_py_path.exists() and not blocks_data_py_path.is_dir()
        if bdj_ok and bdp_ok:
            raise CustomBlocks2Error(
                "Both _blocks_data.json and _blocks_data.py files exist."
                "You should only use one of them for a block group.\n"
                f"Path: {dir_path.as_posix()}")

        try:
            local_scope: dict[str, Any] = load_jsonc(local_scope_path).data
            if not isinstance(local_scope, dict):
                raise CustomBlocks2Error(
                    "The _scope.json file must be a dictionary.\n"
                    f"Path: {local_scope_path.as_posix()}")
        except (JSONDecodeError, OSError) as e:
            raise CustomBlocks2Error(
                "Failed to load the _scope.json file.\n"
                f"Path: {local_scope_path.as_posix()}\n"
                f"Error: {str(e)}")

        if bdj_ok:  # JSON file but not Python file
            yield BlocksData(blocks_data_json_path, scope | local_scope)
        elif bdp_ok:  # Python file but not JSON file
            yield BlocksData(blocks_data_py_path, scope | local_scope)
        else: # None
            continue

class FilterConfig:
    '''
    A class that holds the filter cnofig passed to the script using the
    sys.argv.
    '''
    def __init__(self, scope_path: Path):
        self.scope_path = scope_path

    @staticmethod
    def from_argv() -> FilterConfig:
        '''Loads the filter config from the command line arguments.'''
        if len(sys.argv) > 1:
            config_walker = JSONWalker(json.loads(sys.argv[1]))
            scope_path = config_walker / "scope_path"
            if scope_path.exists:
                if not isinstance(scope_path.data, str):
                    raise CustomBlocks2Error(
                        "The 'scope_path' in the filter config must be a string.")
                return FilterConfig(scope_path=DATA_PATH / scope_path.data)
        return FilterConfig(scope_path=FILTER_DATA_DIR / "scope.json")

def main():
    config = FilterConfig.from_argv()
    try:
        scope = load_jsonc(config.scope_path).data
        if not isinstance(scope, dict):
            raise CustomBlocks2Error(
                "The scope file must be a dictionary.\n"
                f"Path: {config.scope_path.as_posix()}"
            )
    except (JSONDecodeError, OSError):
        raise CustomBlocks2Error(
            "Failed to load the scope file.\n"
            f"Path: {config.scope_path.as_posix()}")
    scope = scope | {
        'true': True, 'false': False, 'math': math, 'uuid': uuid,
        'Path': Path
    }

    for block_data in yield_block_data_files(scope):
        block_data.generate()
    RpBlocksJson.get().save_if_not_empty()
    BpAnimationControllerJson.get().save_if_not_empty()
    Lang.get().save_if_not_empty()
    RpAttachableAnimationJson.get().save_if_not_empty()
    RpCubicAttachableAssets.get().save_if_not_empty()

if __name__ == "__main__":
    try:
        main()
    except CustomBlocks2Error as e:
        print_red(str(e))
        sys.exit(1)

