'''
This file is based on the code from:  https://github.com/Nusiq/regolith-filters

MIT License

Copyright (c) 2021 Nusiq

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''
from enum import Enum, auto
from typing import Dict, List


class ListMergePolicy(Enum):
    GREATER_LENGHT = auto()
    SMALLER_LENGHT = auto()
    B_LENGHT = auto()
    APPEND = auto()

def deep_merge_objects(
        a: dict | list, b: dict | list,
        list_merge_policy=ListMergePolicy.GREATER_LENGHT):
    '''
    Merges two JSON objeccts A and B recursively.  In case of conflicts (
    situations where merging is not possible) the value from B overwrites value
    from A. The function doesn't always create a copy of parts of A and B.
    Sometimes uses references to objects that already exist to A or B which
    means that editing returned structure may edit some valeus in A or B.
    '''
    # in A and in B
    if type(a) != type(b):  # different types unable to merge
        return b
    # Both types are the same
    if isinstance(a, dict):  # Both types are dicts
        return deep_merge_dicts(a, b, list_merge_policy)
    elif isinstance(a, list):  # Both types are lists
        return deep_merge_lists(a, b, list_merge_policy)
    # Both types are smoething unknown
    return b

def deep_merge_dicts(
        a: Dict, b: Dict, list_merge_policy=ListMergePolicy.GREATER_LENGHT):
    '''
    Merges two dictionaries A and B recursively. In case of conflicts (
    situations where merging is not possible) the value from B overwrites value
    from A.
    '''
    result = {}
    # a.keys() | b.keys() could be used but it doesn't preserve order
    keys = list(a.keys()) + list(b.keys())
    used_keys = set()
    for k in keys:
        if k in used_keys:
            continue
        used_keys.add(k)
        if k in b:
            if k not in a: # in B not in A
                result[k] = b[k]
                continue
            result[k] = deep_merge_objects(a[k], b[k], list_merge_policy)
        elif k in a:  # in A not in B
            result[k] = a[k]
    return result

def deep_merge_lists(
        a: List, b: List, list_merge_policy=ListMergePolicy.GREATER_LENGHT):
    '''
    Merges two lists A and B recursively. In case of conflicts (
    situations where merging is not possible) the value from B overwrites value
    from A.
    '''
    # GREATER_LENGHT is the default
    # if list_merge_policy is ListMergePolicy.GREATER_LENGHT:
    list_len = max(len(a), len(b))
    if list_merge_policy is ListMergePolicy.SMALLER_LENGHT:
        list_len = min(len(a), len(b))
    elif list_merge_policy is ListMergePolicy.B_LENGHT:
        list_len = len(b)
    elif list_merge_policy is ListMergePolicy.APPEND:
        for b_item in b:
            a.append(b_item)
        return a
    result = [None]*list_len
    for i in range(list_len):
        if i < len(b):
            if i >= len(a): # in B not in A
                result[i] = b[i]
                continue
            # in B and in A
            result[i] = deep_merge_objects(a[i], b[i], list_merge_policy)
        elif i < len(a):  # in A not in B
            result[i] = a[i]
    return result
