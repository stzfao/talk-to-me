"""TOON conversion layer using python-toon. Token saver trial: 30-60% token reduction
claimed by the repo https://github.com/xaviviro/python-toon

JSON -> TOON before passing CRM data to the LLM (saving here)
TOON -> JSON when parsing LLM structured output back. May not need this though will see

If your CRM connection is directly to the database you can use
https://github.com/ameyakhot/toondb instead. No JSON middleman
"""

from toon import encode, decode


def to_toon(data: dict) -> str:
    return encode(data)


def from_toon(toon_str: str) -> dict:
    return decode(toon_str)
