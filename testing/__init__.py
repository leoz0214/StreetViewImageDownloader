import pathlib
import sys


sys.path.append(str(pathlib.Path(__file__).parent.parent / "src"))


TEST_OUTPUT_FOLDER = pathlib.Path(__file__).parent / "test_outputs"
TEST_OUTPUT_FOLDER.mkdir(exist_ok=True)
