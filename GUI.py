from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QLabel, QCheckBox, QLineEdit, QToolTip, QSlider, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QFont, QIntValidator
import qtawesome as qta
from data_processing import load_and_plot_file, update_plot
from backend import show_time_range_controls, validate_input, apply_time_range, update_pan, update_zoom, validate_custom_filter


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("MKG wizualizacja")
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)

        self.data = None
        self.current_time_from = None
        self.current_time_to = None

        self.top_layout = QHBoxLayout()
        self.top_layout.setSpacing(0)
        self.top_layout.addStretch()

        QToolTip.setFont(QFont('SansSerif', 10))

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
        self.setFixedSize(400, 130)

        self.range_layout = QVBoxLayout()
        self.time_range_label = QLabel("Specify Time Range (seconds):")
        self.range_layout.addWidget(self.time_range_label, alignment=Qt.AlignTop)
        self.time_range_label.hide()

        self.time_from_input = QLineEdit()
        self.time_from_input.setPlaceholderText("From")
        self.time_from_input.setFixedWidth(185)
        self.time_from_input.editingFinished.connect(lambda: validate_input(self, self.time_from_input, "from"))
        self.range_layout.addWidget(self.time_from_input, alignment=Qt.AlignTop)
        self.time_from_input.hide()

        self.error_from_label = QLabel("")
        self.error_from_label.setStyleSheet("color: red; font-size: 12px;")
        self.range_layout.addWidget(self.error_from_label, alignment=Qt.AlignTop)
        self.error_from_label.hide()

        self.time_to_input = QLineEdit()
        self.time_to_input.setPlaceholderText("To")
        self.time_to_input.setFixedWidth(185)
        self.time_to_input.editingFinished.connect(lambda: validate_input(self, self.time_to_input, "to"))
        self.range_layout.addWidget(self.time_to_input, alignment=Qt.AlignTop)
        self.time_to_input.hide()

        self.error_to_label = QLabel("")
        self.error_to_label.setStyleSheet("color: red; font-size: 12px;")
        self.range_layout.addWidget(self.error_to_label, alignment=Qt.AlignTop)
        self.error_to_label.hide()

        self.set_time_button = QPushButton("Set Time Range")
        self.set_time_button.setStyleSheet("""
                QPushButton {
                    background-color: #2d89ef;
                    color: white;
                    border-radius: 10px;
                    padding: 5px 15px;
                    border: none;
                    text-align: center;
                    width: 90px;
                }
                QPushButton:hover {
                    background-color: #1e70c1;
                }
            """)
        self.set_time_button.clicked.connect(lambda: apply_time_range(self))
        self.set_time_button.setFixedWidth(185)
        self.range_layout.addWidget(self.set_time_button, alignment=Qt.AlignTop)
        self.set_time_button.hide()

        self.filters_layout = QVBoxLayout()

        self.filters_label = QLabel("Filters:")
        self.filters_label.setStyleSheet("font-size: 14px;")

        self.filters_defined_layout = QVBoxLayout()
        self.filters_defined_layout.addWidget(self.filters_label, alignment=Qt.AlignTop)

        self.lowpass_filter = QCheckBox("Lowpass")
        self.lowpass_filter.stateChanged.connect(lambda: update_plot(self, self.data))
        self.filters_defined_layout.addWidget(self.lowpass_filter, alignment=Qt.AlignTop)

        self.highpass_filter = QCheckBox("Highpass")
        self.highpass_filter.stateChanged.connect(lambda: update_plot(self, self.data))
        self.filters_defined_layout.addWidget(self.highpass_filter, alignment=Qt.AlignTop)

        self.filter_50hz = QCheckBox("50Hz")
        self.filter_50hz.stateChanged.connect(lambda: update_plot(self, self.data))
        self.filters_defined_layout.addWidget(self.filter_50hz, alignment=Qt.AlignTop)

        self.filter_100hz = QCheckBox("100Hz")
        self.filter_100hz.stateChanged.connect(lambda: update_plot(self, self.data))
        self.filters_defined_layout.addWidget(self.filter_100hz, alignment=Qt.AlignTop)

        self.filter_150hz = QCheckBox("150Hz")
        self.filter_150hz.stateChanged.connect(lambda: update_plot(self, self.data))
        self.filters_defined_layout.addWidget(self.filter_150hz, alignment=Qt.AlignTop)

        self.custom_filters_layout = QVBoxLayout()

        self.custom_filter_1_input = QLineEdit()
        self.custom_filter_1_input.setPlaceholderText("1-999Hz")
        self.custom_filter_1_input.setFixedWidth(85)
        self.custom_filter_1_validator = QIntValidator(1, 999, self)
        self.custom_filter_1_input.setValidator(self.custom_filter_1_validator)
        self.custom_filter_1_input.textChanged.connect(lambda: validate_custom_filter(self.custom_filter_1_input, self.custom_filter_1_apply))
        self.custom_filters_layout.addWidget(self.custom_filter_1_input, alignment=Qt.AlignTop)

        self.custom_filter_1_apply = QCheckBox("Apply")
        self.custom_filter_1_apply.setEnabled(False)
        self.custom_filter_1_apply.stateChanged.connect(lambda: update_plot(self, self.data))
        self.custom_filters_layout.addWidget(self.custom_filter_1_apply, alignment=Qt.AlignTop)

        self.custom_filter_2_input = QLineEdit()
        self.custom_filter_2_input.setPlaceholderText("1-999Hz")
        self.custom_filter_2_input.setFixedWidth(85)
        self.custom_filter_2_validator = QIntValidator(1, 999, self)
        self.custom_filter_2_input.setValidator(self.custom_filter_2_validator)
        self.custom_filter_2_input.textChanged.connect(lambda: validate_custom_filter(self.custom_filter_2_input, self.custom_filter_2_apply))
        self.custom_filters_layout.addWidget(self.custom_filter_2_input, alignment=Qt.AlignTop)

        self.custom_filter_2_apply = QCheckBox("Apply")
        self.custom_filter_2_apply.setEnabled(False)
        self.custom_filter_2_apply.stateChanged.connect(lambda: update_plot(self, self.data))
        self.custom_filters_layout.addWidget(self.custom_filter_2_apply, alignment=Qt.AlignTop)

        self.filters_label.hide()
        self.lowpass_filter.hide()
        self.highpass_filter.hide()
        self.filter_50hz.hide()
        self.filter_100hz.hide()
        self.filter_150hz.hide()
        self.custom_filter_1_input.hide()
        self.custom_filter_1_apply.hide()
        self.custom_filter_2_input.hide()
        self.custom_filter_2_apply.hide()

        self.range_and_filters_layout = QHBoxLayout()
        self.range_and_filters_layout.addLayout(self.range_layout)
        self.range_and_filters_layout.addLayout(self.filters_defined_layout)
        self.range_and_filters_layout.addLayout(self.custom_filters_layout)

        switch_style = """
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
            """

        self.lowpass_filter.setStyleSheet(switch_style)
        self.highpass_filter.setStyleSheet(switch_style)
        self.filter_50hz.setStyleSheet(switch_style)
        self.filter_100hz.setStyleSheet(switch_style)
        self.filter_150hz.setStyleSheet(switch_style)
        self.custom_filter_1_apply.setStyleSheet(switch_style)
        self.custom_filter_2_apply.setStyleSheet(switch_style)

        spacer = QSpacerItem(30, 0, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        self.range_and_filters_layout.addItem(spacer)
        self.range_layout.setContentsMargins(0, 0, 50, 0)
        self.filters_defined_layout.setContentsMargins(0, 0, 30, 0)
        self.custom_filters_layout.setContentsMargins(0, 20, 0, 0)

        self.range_and_filters_layout.setContentsMargins(10, 10, 10, 10)

        self.layout.addLayout(self.range_and_filters_layout)

        self.canvas_layout = QVBoxLayout()
        self.layout.addLayout(self.canvas_layout)

        self.central_widget = QWidget()
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)
        self.canvas_frame = None
        self.change_theme(self.toggle_theme.checkState())

        self.slider_layout = QHBoxLayout()

        self.pan_slider = QSlider(Qt.Horizontal)
        self.pan_slider.setMinimum(0)
        self.pan_slider.setMaximum(100)
        self.pan_slider.setValue(0)
        self.pan_slider.setEnabled(False)
        self.pan_slider.valueChanged.connect(lambda value: update_pan(self, value))
        self.slider_layout.addWidget(self.pan_slider, alignment=Qt.AlignLeft)
        self.pan_slider.hide()

        self.pan_label = QLabel("Scroll")
        self.slider_layout.addWidget(self.pan_label, alignment=Qt.AlignLeft)
        self.pan_label.hide()

        self.slider_layout.addStretch()

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(1)
        self.zoom_slider.setMaximum(100)
        self.zoom_slider.setValue(1)
        self.zoom_slider.valueChanged.connect(lambda value: update_zoom(self, value))
        self.slider_layout.addWidget(self.zoom_slider, alignment=Qt.AlignRight)
        self.zoom_slider.hide()

        self.zoom_label = QLabel("Zoom")
        self.slider_layout.addWidget(self.zoom_label, alignment=Qt.AlignLeft)
        self.zoom_label.hide()

        self.layout.addLayout(self.slider_layout)

    def show_time_range_controls(self):
        show_time_range_controls(self)

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
                        QLineEdit {
                            background-color: #444;
                            color: #f0f0f0;
                            border: 1px solid #555;
                            border-radius: 10px;
                            padding: 5px;
                            size: 10px;
                        }
                        QLineEdit:focus {
                            border: 1px solid #888;
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
                        QLineEdit {
                            background-color: white;
                            color: #333;
                            border: 1px solid #ccc;
                            border-radius: 10px;
                            padding: 5px;
                            width: 10px;
                        }
                            QLineEdit:focus {
                            border: 1px solid #2d89ef;
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

        if self.current_time_from is not None and self.current_time_to is not None:
            filtered_data = self.data[(self.data['time'] >= self.current_time_from) & (self.data['time'] <= self.current_time_to)]
            update_plot(self, filtered_data)
        elif self.data is not None:
            update_plot(self, self.data)
