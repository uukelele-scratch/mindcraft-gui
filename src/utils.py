from PyQt5.QtWidgets import (
    QWidget,
)
from PyQt5.QtGui import QFont

def set_font_size(item: QWidget, size: int | float):
    item.setFont(QFont(QFont().family(), size))