"""Private Utility functions for the API."""
import ctypes
import pathlib


CPP_CONVERSION_LIBARY = pathlib.Path(__file__).parent / "cpp" / "conversion.so"


def _split_array(array: list, parts: int) -> list[list]:
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
    return ctypes.CDLL(str(CPP_CONVERSION_LIBARY))