"""Unit Tests the utils.py module."""
import unittest

import __init__
from _utils import _split_array


class Test_utils(unittest.TestCase):
    
    def test_split_array(self) -> None:
        self.assertEqual(
            _split_array([1, 2, 3, 4, 5], 3), [[1, 2,], [3, 4], [5]])
        self.assertEqual(
            _split_array([1, 2, 3,], 4), [[1], [2], [3], []])
        self.assertEqual(
            _split_array(["a", "b", "c"], 1), [["a", "b", "c"]])
        

if __name__ == "__main__":
    unittest.main()
