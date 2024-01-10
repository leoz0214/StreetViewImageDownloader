import pathlib
import sys
from ctypes import windll


sys.path.append(str(pathlib.Path(__file__).parent.parent))
sys.path.append(str(pathlib.Path(__file__).parent))

# Make GUI DPI aware - significant GUI quality improvement.
windll.shcore.SetProcessDpiAwareness(True)
