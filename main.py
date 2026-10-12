import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from PySide6 import QtWidgets
from src.app import StarScreamWindow

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = StarScreamWindow()
    window.show()
    sys.exit(app.exec())
