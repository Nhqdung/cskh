"""
Application UI Styling and Color Palette (Modern CSKH Professional Theme).
"""

MAIN_STYLESHEET = """
QMainWindow {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
    font-size: 13px;
}

QWidget {
    color: #cdd6f4;
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
}

QTabWidget::pane {
    border: 1px solid #313244;
    background-color: #181825;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #181825;
    color: #a6adc8;
    padding: 10px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
    border: 1px solid #313244;
    border-bottom: none;
}

QTabBar::tab:selected {
    background-color: #313244;
    color: #89b4fa;
    border-color: #89b4fa;
}

QTabBar::tab:hover {
    background-color: #45475a;
    color: #ffffff;
}

QGroupBox {
    background-color: #181825;
    border: 1px solid #313244;
    border-radius: 8px;
    margin-top: 24px;
    font-size: 13px;
    font-weight: bold;
    padding-top: 16px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    color: #89b4fa;
    background-color: #1e1e2e;
    border-radius: 4px;
}

QPushButton {
    background-color: #89b4fa;
    color: #11111b;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #b4befe;
}

QPushButton:pressed {
    background-color: #74c7ec;
}

QPushButton:disabled {
    background-color: #45475a;
    color: #6c7086;
}

QPushButton#btn_danger {
    background-color: #f38ba8;
    color: #11111b;
}

QPushButton#btn_danger:hover {
    background-color: #eba0ac;
}

QPushButton#btn_secondary {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
}

QPushButton#btn_secondary:hover {
    background-color: #45475a;
}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox, QDateEdit {
    background-color: #11111b;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus {
    border: 1px solid #89b4fa;
}

QTableWidget {
    background-color: #11111b;
    border: 1px solid #313244;
    border-radius: 6px;
    gridline-color: #313244;
    selection-background-color: #45475a;
    selection-color: #cdd6f4;
}

QHeaderView::section {
    background-color: #181825;
    color: #89b4fa;
    padding: 6px;
    border: 1px solid #313244;
    font-weight: bold;
}

QLabel {
    color: #cdd6f4;
}

QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background: #181825;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #585b70;
}
"""
