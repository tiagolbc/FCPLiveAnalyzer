"""Dark theme (Qt style sheet) and plot colours."""

BG = "#0f1115"
PANEL = "#171a21"
PANEL2 = "#1e222b"
BORDER = "#2a2f3a"
TEXT = "#e6e8ee"
MUTED = "#9aa3b2"
ACCENT = "#3b82f6"
LTAS_CURVE = "#f5f5f5"
GLOBAL_CURVE = "#7c8496"
TREND = "#facc15"
BUZZ = "#c084fc"
WARN = "#f59e0b"

QSS = f"""
* {{ font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 10pt; color: {TEXT}; }}
QMainWindow, QDialog {{ background: {BG}; }}
QWidget#central {{ background: {BG}; }}
QToolBar {{ background: {PANEL}; border: none; border-bottom: 1px solid {BORDER}; padding: 4px; spacing: 4px; }}
QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 8px; padding: 6px 10px; }}
QToolButton:hover {{ background: {PANEL2}; border-color: {BORDER}; }}
QToolButton:checked {{ background: #7f1d1d; border-color: #ef4444; }}
QToolButton:disabled {{ color: #5b6270; }}
QFrame#card {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 12px; }}
QLabel#cardTitle {{ color: {MUTED}; font-size: 9pt; }}
QLabel#bigValue {{ font-size: 34pt; font-weight: 600; }}
QLabel#midValue {{ font-size: 18pt; font-weight: 600; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#badge {{ background: #3b2a55; color: #e9d5ff; border-radius: 6px; padding: 1px 6px; font-size: 8pt; }}
QLabel#warn {{ color: #fde68a; }}
QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox {{ background: {PANEL2}; border: 1px solid {BORDER}; border-radius: 6px; padding: 4px 6px; }}
QComboBox QAbstractItemView {{ background: {PANEL2}; selection-background-color: {ACCENT}; }}
QPushButton {{ background: {PANEL2}; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px 14px; }}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton#primary {{ background: {ACCENT}; border-color: {ACCENT}; color: white; }}
QCheckBox {{ spacing: 6px; }}
QTabWidget::pane {{ border: 1px solid {BORDER}; border-radius: 10px; background: {PANEL}; top: -1px; }}
QTabBar::tab {{ background: transparent; padding: 6px 14px; color: {MUTED}; }}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}
QStatusBar {{ background: {PANEL}; color: {MUTED}; border-top: 1px solid {BORDER}; }}
QProgressBar {{ background: {PANEL2}; border: 1px solid {BORDER}; border-radius: 6px; text-align: center; height: 14px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 6px; }}
QTableWidget {{ background: {PANEL}; gridline-color: {BORDER}; border: none; }}
QHeaderView::section {{ background: {PANEL2}; color: {MUTED}; border: none; padding: 4px; }}
QTextBrowser {{ background: {PANEL}; border: none; }}
QScrollArea {{ border: none; background: transparent; }}
QToolTip {{ background: {PANEL2}; color: {TEXT}; border: 1px solid {BORDER}; }}
"""
