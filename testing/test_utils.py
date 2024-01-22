"""Unit Tests the utils.py module."""
import unittest

import __init__
from _utils import _split_array, _load_cpp_conversion_library, _in_rectangle


class Test_utils(unittest.TestCase):
    
    def test_split_array(self) -> None:
        self.assertEqual(
            _split_array([1, 2, 3, 4, 5], 3), [[1, 2,], [3, 4], [5]])
        self.assertEqual(
            _split_array([1, 2, 3,], 4), [[1], [2], [3], []])
        self.assertEqual(
            _split_array(["a", "b", "c"], 1), [["a", "b", "c"]])
    
    def test_load_cpp_conversion_library(self) -> None:
        _load_cpp_conversion_library()
    
    def test_in_rectangle(self) -> None:
        self.assertTrue(_in_rectangle((0, 0), (5, 5), (3, 4)))
        self.assertTrue(_in_rectangle((-3, -2), (-2, -1), (-3, -2)))
        self.assertTrue(_in_rectangle((5, 8), (7, 9), (6, 8)))
        self.assertFalse(_in_rectangle((0, 0), (6, 3), (8, 4)))
        self.assertFalse(_in_rectangle((-1, -1), (4, 5), (3, -2)))
        self.assertFalse(_in_rectangle((2, 3), (4, 5), (2, 2)))
        

if __name__ == "__main__":
    unittest.main()
