from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QLabel, QCheckBox, QLineEdit, QSlider, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QIntValidator, QIcon
import qtawesome as qta
from data_processing import load_and_plot_file, update_plot
from backend import show_controls, validate_input, apply_time_range, update_pan, update_zoom, validate_custom_filter, save_data, state_change, handle_bandpass_apply_toggle, validate_bandpass_values, handle_filter_toggle
from qtrangeslider import QLabeledDoubleRangeSlider
from live_visualization import RealTimePlotWindow, reset_com_port
import gc


class MainWindow(QMainWindow):
    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange or event.type() == QEvent.ActivationChange:
            state_change(self)
        super().changeEvent(event)

    def __init__(self):
        super().__init__()

        self.dark_mode = None
        self.setWindowTitle("MKG wizualizacja")
        self.setWindowIcon(QIcon('./images/Icon.png'))
        self.is_active = True

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)

        self.data = None
        self.current_time_from = None
        self.current_time_to = None

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

        # Kontener na przyciski
        self.start_layout = QHBoxLayout()

        # Przycisk analizy z pliku
        self.file_analysis_button = QPushButton("Analiza danych z pliku")
        self.file_analysis_button.setIcon(qta.icon('fa5s.file-import', color='white'))
        self.file_analysis_button.setStyleSheet("""
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
        self.file_analysis_button.clicked.connect(self.start_file_analysis)
        self.start_layout.addWidget(self.file_analysis_button)

        # Przycisk analizy w czasie rzeczywistym
        self.real_time_analysis_button = QPushButton("Analiza danych w czasie rzeczywistym")
        self.real_time_analysis_button.setIcon(qta.icon('fa5s.chart-line', color='white'))
        self.real_time_analysis_button.setStyleSheet("""
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
        self.real_time_analysis_button.clicked.connect(self.start_real_time_analysis)
        self.start_layout.addWidget(self.real_time_analysis_button)

        self.layout.addLayout(self.start_layout)

        # Flaga kontroli otwartego okna analizy w czasie rzeczywistym
        self.real_time_window = None

        self.setFixedSize(500, 150)

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
        self.lowpass_filter.stateChanged.connect(lambda: handle_filter_toggle(self, 'lowpass'))
        self.filters_defined_layout.addWidget(self.lowpass_filter, alignment=Qt.AlignTop)

        self.highpass_filter = QCheckBox("Highpass")
        self.highpass_filter.stateChanged.connect(lambda: handle_filter_toggle(self, 'highpass'))
        self.filters_defined_layout.addWidget(self.highpass_filter, alignment=Qt.AlignTop)

        self.filter_50hz = QCheckBox("50Hz")
        self.filter_50hz.stateChanged.connect(lambda: handle_filter_toggle(self, '50hz'))
        self.filters_defined_layout.addWidget(self.filter_50hz, alignment=Qt.AlignTop)

        self.filter_100hz = QCheckBox("100Hz")
        self.filter_100hz.stateChanged.connect(lambda: handle_filter_toggle(self, '100hz'))
        self.filters_defined_layout.addWidget(self.filter_100hz, alignment=Qt.AlignTop)

        self.filter_150hz = QCheckBox("150Hz")
        self.filter_150hz.stateChanged.connect(lambda: handle_filter_toggle(self, '150hz'))
        self.filters_defined_layout.addWidget(self.filter_150hz, alignment=Qt.AlignTop)

        self.custom_filters_layout = QVBoxLayout()

        self.custom_filter1_layout = QHBoxLayout()
        self.custom_filter_1_input = QLineEdit()
        self.custom_filter_1_input.setPlaceholderText("1-999Hz")
        self.custom_filter_1_input.setFixedWidth(100)
        self.custom_filter_1_validator = QIntValidator(1, 999, self)
        self.custom_filter_1_input.setValidator(self.custom_filter_1_validator)
        self.custom_filter_1_input.textChanged.connect(lambda: validate_custom_filter(self.custom_filter_1_input, self.custom_filter_1_apply))
        self.custom_filter1_layout.addWidget(self.custom_filter_1_input, alignment=Qt.AlignTop)

        self.custom_filter_1_apply = QCheckBox("Apply")
        self.custom_filter_1_apply.setEnabled(False)
        self.custom_filter_1_apply.stateChanged.connect(lambda: handle_filter_toggle(self, 'custom_filter_1'))
        self.custom_filter1_layout.addWidget(self.custom_filter_1_apply, alignment=Qt.AlignLeft)

        self.custom_filter2_layout = QHBoxLayout()
        self.custom_filter_2_input = QLineEdit()
        self.custom_filter_2_input.setPlaceholderText("1-999Hz")
        self.custom_filter_2_input.setFixedWidth(100)
        self.custom_filter_2_validator = QIntValidator(1, 999, self)
        self.custom_filter_2_input.setValidator(self.custom_filter_2_validator)
        self.custom_filter_2_input.textChanged.connect(lambda: validate_custom_filter(self.custom_filter_2_input, self.custom_filter_2_apply))
        self.custom_filter2_layout.addWidget(self.custom_filter_2_input, alignment=Qt.AlignTop)

        self.custom_filter_2_apply = QCheckBox("Apply")
        self.custom_filter_2_apply.setEnabled(False)
        self.custom_filter_2_apply.stateChanged.connect(lambda: handle_filter_toggle(self, 'custom_filter_2'))
        self.custom_filter2_layout.addWidget(self.custom_filter_2_apply, alignment=Qt.AlignLeft)

        self.bandpass_layout = QHBoxLayout()
        self.bandpass_slider = QLabeledDoubleRangeSlider(Qt.Horizontal)
        self.bandpass_slider.setRange(1, 400)
        self.bandpass_slider.setValue((20, 200))
        self.bandpass_slider.setFixedWidth(100)
        self.bandpass_slider.setSingleStep(1)
        self.bandpass_slider.setDecimals(0)

        self.bandpass_slider.setStyleSheet("""
            QSlider{
                qproperty-barColor: #74aeed;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #ddd;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2d89ef;
                width: 15px;
                height: 10px;
                margin: -5px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #1e70c1;
            }
        """)

        self.bandpass_slider.valueChanged.connect(lambda: validate_bandpass_values(self))
        self.bandpass_layout.addWidget(self.bandpass_slider, alignment=Qt.AlignTop)
        self.bandpass_slider.setEdgeLabelMode(None)

        self.bandpass_apply = QCheckBox("Apply")
        self.bandpass_apply.stateChanged.connect(lambda: handle_bandpass_apply_toggle(self))
        self.bandpass_apply.setFixedHeight(70)
        self.bandpass_layout.addWidget(self.bandpass_apply, alignment=Qt.AlignTop)

        self.custom_filters_layout.addLayout(self.custom_filter1_layout)
        self.custom_filters_layout.addLayout(self.custom_filter2_layout)
        self.custom_filters_layout.addLayout(self.bandpass_layout)

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
        self.bandpass_apply.setStyleSheet(switch_style)

        spacer = QSpacerItem(30, 0, QSizePolicy.MinimumExpanding, QSizePolicy.Minimum)
        self.range_and_filters_layout.addItem(spacer)
        self.range_layout.setContentsMargins(0, 0, 50, 0)
        self.filters_defined_layout.setContentsMargins(0, 0, 30, 0)
        self.custom_filters_layout.setContentsMargins(0, 20, 0, 0)

        self.range_and_filters_layout.setContentsMargins(10, 10, 10, 10)

        self.save_options_layout = QVBoxLayout()

        self.file_name_input = QLineEdit()
        self.file_name_input.setPlaceholderText("File Name")
        self.file_name_input.setFixedWidth(200)
        self.save_options_layout.addWidget(self.file_name_input, alignment=Qt.AlignBottom)
        self.file_name_input.hide()

        self.save_options_layout.setContentsMargins(0, 20, 0, 0)

        self.buttons_layout = QHBoxLayout()

        self.save_txt = QCheckBox(".txt")
        self.save_txt.setStyleSheet(switch_style)
        self.save_txt.hide()
        self.save_tsv = QCheckBox(".tsv")
        self.save_tsv.setStyleSheet(switch_style)
        self.save_tsv.hide()
        self.save_xlsx = QCheckBox(".xlsx")
        self.save_xlsx.setStyleSheet(switch_style)
        self.save_xlsx.hide()

        self.buttons_layout.addWidget(self.save_txt, alignment=Qt.AlignCenter)
        self.buttons_layout.addWidget(self.save_tsv, alignment=Qt.AlignCenter)
        self.buttons_layout.addWidget(self.save_xlsx, alignment=Qt.AlignCenter)
        self.save_options_layout.addLayout(self.buttons_layout)

        self.save_button = QPushButton("Save")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #2d89ef;
                color: white;
                border-radius: 10px;
                padding: 5px 15px;
                border: none;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #1e70c1;
            }
        """)
        self.save_button.clicked.connect(lambda value: save_data(self))
        self.save_button.setFixedWidth(200)
        self.save_options_layout.addWidget(self.save_button, alignment=Qt.AlignBottom)
        self.save_button.hide()

        self.save_options_layout.setContentsMargins(0, 0, 0, 0)

        self.range_and_filters_layout.addLayout(self.save_options_layout)
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
        self.pan_slider.setFixedWidth(200)
        self.pan_slider.valueChanged.connect(lambda value: update_pan(self, value))
        self.slider_layout.addWidget(self.pan_slider, alignment=Qt.AlignLeft)
        self.pan_slider.hide()

        self.pan_label = QLabel("Scroll")
        self.slider_layout.addWidget(self.pan_label, alignment=Qt.AlignLeft)
        self.pan_label.hide()

        self.slider_layout.addStretch()

        self.zoom_label = QLabel("Zoom")
        self.slider_layout.addWidget(self.zoom_label, alignment=Qt.AlignRight)
        self.zoom_label.hide()

        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(1)
        self.zoom_slider.setMaximum(100)
        self.zoom_slider.setValue(1)
        self.zoom_slider.setFixedWidth(200)
        self.zoom_slider.valueChanged.connect(lambda value: update_zoom(self, value))
        self.slider_layout.addWidget(self.zoom_slider, alignment=Qt.AlignLeft)
        self.zoom_slider.hide()

        self.layout.addLayout(self.slider_layout)

    def start_file_analysis(self):
        """Przełącz do trybu analizy danych z pliku."""
        load_and_plot_file(self)

    def start_real_time_analysis(self):
        if not hasattr(self, 'real_time_window') or self.real_time_window is None:
            self.real_time_window = RealTimePlotWindow()
            self.real_time_window.closed.connect(self.reset_real_time_window)  # Połącz sygnał z metodą
            self.real_time_window.show()
        else:
            print("Okno analizy w czasie rzeczywistym jest już otwarte.")

    def reset_real_time_window(self):
        print("Resetowanie flagi real_time_window.")
        self.real_time_window = None
        import gc
        gc.collect()  # Wymuś zwolnienie pamięci

    def show_controls(self):
        show_controls(self)

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
                QDoubleSpinBox, QSpinBox {
                    background: transparent;
                    border: none;
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
                QDoubleSpinBox, QSpinBox {
                    background: transparent;
                    border: none;
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
