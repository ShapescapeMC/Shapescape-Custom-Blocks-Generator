'''
This module contains the exceptions used in the
shapescape_custom_blocks_generator package.
'''

class CustomBlocks2Error(Exception):
    '''Base class for exceptions in this module.'''


def print_red(text: str):
    '''Prints text in red.'''
    for t in text.split('\n'):
        print("\033[91m {}\033[00m".format(t))

def print_yellow(text: str):
    '''Prints text in yellow.'''
    for t in text.split('\n'):
        print("\033[93m {}\033[00m".format(t))