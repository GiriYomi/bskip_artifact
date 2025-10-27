# https://github.com/codelion/openevolve/blob/970812a0e8e3837c48c4813bace564cde4c775a6/openevolve/utils/code_utils.py
# openevolve/utils/code_utils.py
import re
from typing import Dict, List, Optional, Tuple, Union

def parse_evolve_blocks(code: str) -> List[Tuple[int, int, str]]:
    """
    Parse evolve blocks from code

    Args:
        code: Source code with evolve blocks

    Returns:
        List of tuples (start_line, end_line, block_content)
    """
    lines = code.split("\n")
    blocks = []

    in_block = False
    start_line = -1
    block_content = []

    for i, line in enumerate(lines):
        if "# EVOLVE-BLOCK-START" in line:
            in_block = True
            start_line = i
            block_content = []
        elif "# EVOLVE-BLOCK-END" in line and in_block:
            in_block = False
            blocks.append((start_line, i, "\n".join(block_content)))
        elif in_block:
            block_content.append(line)

    return blocks


example_code = """
# EVOLVE-BLOCK-START
def hello_world():
    print("Hello, World!")

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b
# EVOLVE-BLOCK-END

def multiply(a, b):
    return a * b

def divide(a, b):
    return a / b

if __name__ == "__main__":
    hello_world()
# EVOLVE-BLOCK-END
"""

if __name__ == "__main__":
    blocks = parse_evolve_blocks(example_code)
    print(blocks)
