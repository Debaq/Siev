def apply_styles(widget):
    widget.setStyleSheet("""
        QLabel {
            font-size: 14px;
        }
        QLineEdit {
            padding: 5px;
            font-size: 14px;
        }
        QPushButton {
            padding: 10px;
            font-size: 14px;
            background-color: #0099cc;
            color: white;
            border-radius: 5px;
        }
        QPushButton:hover {
            background-color: #0077aa;
        }
    """)
