"""Private Utility functions for the API."""
import ctypes
import pathlib


CPP_CONVERSION_LIBRARY = pathlib.Path(__file__).parent / "cpp/conversion.so"


def _split_array(array: list, parts: int) -> list[list]:
    # Splits a list into N parts as evenly as possible.
    quotient, modulus = divmod(len(array), parts)
    i = 0
    new = [[] for _ in range(parts)]
    part = 0
    while i < len(array):
        new[part] = array[i:i+quotient+bool(modulus)]
        i += quotient + bool(modulus)
        if modulus:
            modulus -= 1
        part += 1
    return new


def _load_cpp_conversion_library() -> ctypes.CDLL:
    # Loads C++ image conversion library.
    return ctypes.CDLL(str(CPP_CONVERSION_LIBRARY))


def _in_rectangle(
    top_left: tuple[int, int], bottom_right: tuple[int, int],
    coordinates: tuple[int, int]
) -> bool:
    # Returns True if coordinates lie in a given rectangle, else False.
    return (
        top_left[0] <= coordinates[0] <= bottom_right[0]
        and top_left[1] <= coordinates[1] <= bottom_right[1])