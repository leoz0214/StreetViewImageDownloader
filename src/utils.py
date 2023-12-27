""""Utility functions for the program."""


def _split_array(array: list, parts: int) -> list[list]:
    quotient, modulus = divmod(len(array), parts)
    i = 0
    new = []
    while i < len(array):
        new.append(array[i:i+quotient+bool(modulus)])
        i += quotient + bool(modulus)
        if modulus:
            modulus -= 1
    return new
