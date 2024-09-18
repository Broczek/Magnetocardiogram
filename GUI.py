from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QPushButton, QWidget, QLabel, QFrame, QCheckBox, QHBoxLayout
import qtawesome as qta
from data_processing import load_and_plot_file, update_plot


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("MKG wizualizacja")
        self.layout = QVBoxLayout()

        self.current_data = None

        self.top_layout = QHBoxLayout()
        self.top_layout.setSpacing(0)
        self.top_layout.addStretch()

        self.setStyleSheet("""
        QLabel {
            font-size: 14px;
        }""")

        self.toggle_theme = QCheckBox()
        self.toggle_theme.setStyleSheet("""
            QCheckBox::indicator {
                width: 40px;
                height: 20px;
                border-radius: 10px;
                background-color: #ccc;
                position: relative;
            }
            QCheckBox::indicator:checked {
                background-color: #2d89ef;
                image: url(./images/dot_black.png);
            }
            QCheckBox::indicator:unchecked {
                background-color: #ccc;
                image: url(./images/dot_white.png);
            }
        """)

        self.toggle_theme.stateChanged.connect(self.change_theme)

        self.theme_label = QLabel("Dark Mode")
        self.theme_label.setStyleSheet("font-size: 14px; padding-bottom: 1px;")

        self.top_layout.addWidget(self.toggle_theme, alignment=Qt.AlignRight)
        self.top_layout.addWidget(self.theme_label, alignment=Qt.AlignRight)
        self.layout.addLayout(self.top_layout)

        self.file_path_label = QLabel("No file selected")
        self.layout.addWidget(self.file_path_label, alignment=Qt.AlignLeft)

        self.load_button = QPushButton(" Load and Plot Data")
        self.load_button.setIcon(qta.icon('fa5s.file-import', color='white'))
        self.load_button.setStyleSheet("""
            QPushButton {
                background-color: #2d89ef;
                color: white;
                border-radius: 15px;
                padding: 10px 20px;
                border: none;
                text-align: center;
                padding-left: 20px;
            }
            QPushButton:hover {
                background-color: #1e70c1;
            }
        """)

        self.load_button.clicked.connect(lambda: load_and_plot_file(self))
        self.layout.addWidget(self.load_button)
        self.central_widget = QWidget()
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)
        self.canvas_frame = None
        self.setFixedSize(400, 100)

    def change_theme(self, state):
        if state == 2:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2c2c2c;
                }
                QLabel {
                    color: #f0f0f0;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #555;
                    color: white;
                    border-radius: 15px;
                    padding: 10px 20px;
                    border: none;
                    text-align: center;
                    padding-left: 20px;
                }
                QPushButton:hover {
                    background-color: #333;
                }
                QCheckBox {
                    color: #f0f0f0;
                }
            """)

            if self.canvas_frame:
                self.canvas_frame.setStyleSheet("""
                    QFrame {
                        border: 1px solid #888888;
                        border-radius: 15px;
                        background-color: #2c2c2c;
                    }
                """)

        else:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f0f0f0;
                }
                QLabel {
                    color: #333;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #2d89ef;
                    color: white;
                    border-radius: 15px;
                    padding: 30px 20px;
                    border: none;
                    text-align: center;
                    padding-left: 20px;
                }
                QPushButton:hover {
                    background-color: #1e70c1;
                }
                QCheckBox {
                    color: #333;
                }
            """)

            if self.canvas_frame:
                self.canvas_frame.setStyleSheet("""
                    QFrame {
                        border: 1px solid #2d89ef;
                        border-radius: 15px;
                        background-color: white;
                    }
                """)

        if self.current_data is not None:
            update_plot(self, self.current_data)
