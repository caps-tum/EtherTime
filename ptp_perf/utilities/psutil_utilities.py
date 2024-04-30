from typing import Dict, Union, List, NamedTuple, Callable


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


# ChatGPT
def hierarchical_apply(
        data1: Union[Dict, List, int, float],
        data2: Union[Dict, List, int, float],
        fun: Callable[[Union[int, float], Union[int, float]], Union[int, float]]
) -> Union[Dict, List, int, float]:
    """
    Recursively compute the difference between numerical values in corresponding
    structures of data1 and data2, maintaining the structure.
    """
    if isinstance(data1, dict) and isinstance(data2, dict):
        # Handle the case where both are dictionaries
        keys = data1.keys() | data2.keys()  # Union of all keys from both dictionaries
        return {key: hierarchical_apply(data1.get(key, 0), data2.get(key, 0), fun) for key in keys}
    elif isinstance(data1, list) and isinstance(data2, list):
        # Handle the case where both are lists
        max_length = max(len(data1), len(data2))
        result = []
        for i in range(max_length):
            val1 = data1[i] if i < len(data1) else 0
            val2 = data2[i] if i < len(data2) else 0
            result.append(hierarchical_apply(val1, val2, fun))
        return result
    elif isinstance(data1, (int, float)) and isinstance(data2, (int, float)):
        # Directly return the difference if both are numbers
        return fun(data1, data2)
    else:
        # Handle cases where one or both are missing or incompatible types
        # Treat missing or non-numeric as zero
        val1 = data1 if isinstance(data1, (int, float)) else 0
        val2 = data2 if isinstance(data2, (int, float)) else 0
        return fun(val1, val2)
