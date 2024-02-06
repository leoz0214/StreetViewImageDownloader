import pathlib
import sys
from ctypes import windll


if hasattr(sys, "_MEIPASS"):
    sys.path.append(f"{sys._MEIPASS}/src") 
else:
    sys.path.append(str(pathlib.Path(__file__).parent.parent))

# Make GUI DPI aware - significant GUI quality improvement.
windll.shcore.SetProcessDpiAwareness(True)
