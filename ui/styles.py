# ui/styles.py - Modern Dark / Apple Dynamic Island Glass Theme

THEME = {
    "bg_island": "rgba(16, 18, 24, 0.96)",
    "bg_card": "rgba(25, 28, 38, 0.7)",
    "bg_card_hover": "rgba(35, 39, 52, 0.85)",
    "bg_input": "rgba(20, 23, 32, 0.85)",
    "border_light": "rgba(255, 255, 255, 0.12)",
    "border_focus": "#0A84FF",
    "text_primary": "#FFFFFF",
    "text_secondary": "#9BA1B0",
    "text_muted": "#606678",
    "accent_blue": "#0A84FF",
    "accent_blue_hover": "#0071E3",
    "accent_green": "#30D158",
    "accent_orange": "#FF9F0A",
    "accent_red": "#FF453A",
    "accent_purple": "#AF52DE",
    "accent_cyan": "#64D2FF",
}

MAIN_STYLE = f"""
QWidget {{
    font-family: "Segoe UI", "Microsoft YaHei", -apple-system, sans-serif;
    color: {THEME['text_primary']};
}}

/* Island main container border */
#IslandContainer {{
    background-color: {THEME['bg_island']};
    border: 1px solid {THEME['border_light']};
    border-radius: 20px;
}}

/* Scrollbar */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 6px;
    margin: 4px 0 4px 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.18);
    min-height: 24px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.32);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* Line Edit / Input */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {THEME['bg_input']};
    border: 1px solid {THEME['border_light']};
    border-radius: 10px;
    padding: 7px 12px;
    color: {THEME['text_primary']};
    font-size: 13px;
    selection-background-color: {THEME['accent_blue']};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {THEME['accent_blue']};
    background-color: rgba(22, 26, 38, 0.95);
}}

/* ComboBox */
QComboBox {{
    background-color: {THEME['bg_input']};
    border: 1px solid {THEME['border_light']};
    border-radius: 8px;
    padding: 5px 10px;
    color: {THEME['text_primary']};
    font-size: 12px;
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: #1A1D27;
    border: 1px solid {THEME['border_light']};
    selection-background-color: {THEME['accent_blue']};
    selection-color: #ffffff;
    outline: none;
    padding: 4px;
}}

/* Date & Time Picker Controls */
QDateTimeEdit, QDateEdit, QTimeEdit {{
    background-color: {THEME['bg_input']};
    border: 1px solid {THEME['border_light']};
    border-radius: 8px;
    padding: 5px 8px;
    color: #FFFFFF;
    font-size: 12px;
    font-weight: 600;
}}
QDateTimeEdit:focus, QDateEdit:focus, QTimeEdit:focus {{
    border: 1px solid {THEME['accent_blue']};
}}
QDateTimeEdit::drop-down, QDateEdit::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border: none;
}}

/* Calendar Widget Popup */
QCalendarWidget QWidget {{
    background-color: #181B26;
    color: #FFFFFF;
}}
QCalendarWidget QToolButton {{
    color: #FFFFFF;
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 4px;
    font-weight: bold;
}}
QCalendarWidget QToolButton:hover {{
    background-color: rgba(255, 255, 255, 0.15);
}}
QCalendarWidget QMenu {{
    background-color: #181B26;
    color: #FFFFFF;
    border: 1px solid {THEME['border_light']};
}}
QCalendarWidget QSpinBox {{
    background-color: #12141D;
    color: #FFFFFF;
    border: 1px solid {THEME['border_light']};
    border-radius: 4px;
}}
QCalendarWidget QAbstractItemView:enabled {{
    background-color: #12141D;
    color: #E2E8F0;
    selection-background-color: {THEME['accent_blue']};
    selection-color: #FFFFFF;
}}

/* Buttons */
QPushButton {{
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid {THEME['border_light']};
    border-radius: 9px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
    color: {THEME['text_primary']};
}}
QPushButton:hover {{
    background-color: rgba(255, 255, 255, 0.15);
    border-color: rgba(255, 255, 255, 0.22);
}}
QPushButton:pressed {{
    background-color: rgba(255, 255, 255, 0.05);
}}

/* Square Icon Buttons (Zero padding so icons & glyphs are never clipped!) */
QPushButton#IconButton {{
    padding: 0px;
    text-align: center;
    border-radius: 8px;
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid {THEME['border_light']};
}}
QPushButton#IconButton:hover {{
    background-color: rgba(255, 255, 255, 0.18);
    border-color: rgba(255, 255, 255, 0.3);
}}
QPushButton#IconButton:pressed {{
    background-color: rgba(255, 255, 255, 0.05);
}}

/* Primary Accent Button */
QPushButton#PrimaryButton {{
    background-color: {THEME['accent_blue']};
    border: 1px solid {THEME['accent_blue']};
    color: #FFFFFF;
    font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{
    background-color: {THEME['accent_blue_hover']};
    border-color: {THEME['accent_blue_hover']};
}}

/* Danger Button */
QPushButton#DangerButton {{
    background-color: rgba(255, 69, 58, 0.15);
    border: 1px solid rgba(255, 69, 58, 0.35);
    color: {THEME['accent_red']};
}}
QPushButton#DangerButton:hover {{
    background-color: rgba(255, 69, 58, 0.3);
}}

/* Success Button */
QPushButton#SuccessButton {{
    background-color: rgba(48, 209, 88, 0.15);
    border: 1px solid rgba(48, 209, 88, 0.35);
    color: {THEME['accent_green']};
}}
QPushButton#SuccessButton:hover {{
    background-color: rgba(48, 209, 88, 0.3);
}}

/* Nav / Tab Buttons */
QPushButton#NavTabButton {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    padding: 7px 12px;
    color: {THEME['text_secondary']};
    font-size: 12px;
    font-weight: 500;
}}
QPushButton#NavTabButton:hover {{
    background-color: rgba(255, 255, 255, 0.08);
    color: {THEME['text_primary']};
}}
QPushButton#NavTabButton[active="true"] {{
    background-color: rgba(255, 255, 255, 0.16);
    color: #FFFFFF;
    font-weight: 600;
}}

/* Filter Tag Buttons */
QPushButton#FilterTag {{
    background-color: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 3px 10px;
    font-size: 11px;
    color: {THEME['text_secondary']};
}}
QPushButton#FilterTag:hover {{
    background-color: rgba(255, 255, 255, 0.12);
    color: {THEME['text_primary']};
}}
QPushButton#FilterTag[active="true"] {{
    background-color: {THEME['accent_blue']};
    border-color: {THEME['accent_blue']};
    color: #FFFFFF;
    font-weight: 600;
}}

/* Checkbox */
QCheckBox {{
    color: {THEME['text_primary']};
    font-size: 13px;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 1.5px solid rgba(255, 255, 255, 0.3);
    background: transparent;
}}
QCheckBox::indicator:hover {{
    border-color: {THEME['accent_blue']};
}}
QCheckBox::indicator:checked {{
    background-color: {THEME['accent_green']};
    border-color: {THEME['accent_green']};
    image: none;
}}

/* Task Card Frame */
QFrame#TaskCard {{
    background-color: {THEME['bg_card']};
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
}}
QFrame#TaskCard:hover {{
    background-color: {THEME['bg_card_hover']};
    border-color: rgba(255, 255, 255, 0.14);
}}

/* Slider */
QSlider::groove:horizontal {{
    height: 4px;
    background: rgba(255, 255, 255, 0.15);
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {THEME['accent_blue']};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: #FFFFFF;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}}
"""
