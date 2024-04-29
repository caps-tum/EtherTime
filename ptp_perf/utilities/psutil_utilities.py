from typing import Dict, Union, List, NamedTuple


# ChatGPT
def recursive_namedtuple_to_dict(item: Union[Dict, NamedTuple]) -> Union[Dict, List]:
    """Recursively convert all namedtuples in a given structure to dictionaries using the _asdict method."""
    if isinstance(item, tuple) and hasattr(item, '_asdict'):
        # Use the _asdict method provided by namedtuple to convert to a dictionary
        return {key: recursive_namedtuple_to_dict(value) for key, value in item._asdict().items()}
    elif isinstance(item, dict):
        # Recursively process each value in the dictionary
        return {key: recursive_namedtuple_to_dict(value) for key, value in item.items()}
    elif isinstance(item, list):
        # Recursively process each item in the list
        return [recursive_namedtuple_to_dict(x) for x in item]
    else:
        # Return the item as is if it is neither a dict, list, nor namedtuple
        return item
