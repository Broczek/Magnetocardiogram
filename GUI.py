import os
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QLabel, QCheckBox, QLineEdit, QSlider, QSpacerItem, QSizePolicy, \
    QMessageBox, QComboBox
from PyQt5.QtGui import QIntValidator, QIcon
import qtawesome as qta
from data_processing import load_and_plot_file, update_plot
from backend import show_controls, validate_input, apply_time_range, update_pan, update_zoom, validate_custom_filter, save_data, state_change, \
    handle_bandpass_apply_toggle, validate_bandpass_values, handle_filter_toggle, refresh_plot
from qtrangeslider import QLabeledDoubleRangeSlider
from live_visualization import RealTimePlotWindow
from backend import IMAGES_DIR, DOT_BLACK_PATH, DOT_WHITE_PATH


class MainWindow(QMainWindow):
    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange or event.type() == QEvent.ActivationChange:
            state_change(self)
        super().changeEvent(event)

    def __init__(self):
        super().__init__()

        self.dark_mode = None
        self.setWindowTitle("MKG visualisation")
        self.setWindowIcon(QIcon(os.path.join(IMAGES_DIR, "Icon.png")))
        self.is_active = True

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignTop)

        self.data = None
        self.current_time_from = None
        self.current_time_to = None
        self.sampling_rate = None
        self.available_channels = []
        self.primary_channel = None
        self.reference_channel = None
        self.lowpass_cutoff = 120.0
        self.highpass_cutoff = 0.5
        self.baseline_window_sec = 0.7
        self.baseline_polyorder = 3
        self.savgol_window_sec = 0.025
        self.savgol_polyorder = 3
        self.processing_profile = "Auto"
        self.last_detected_profile = None
        self.hampel_window = 21
        self.hampel_sigmas = 3.0
        self.peak_prominence = None
        self.last_feature_summary = {}
        self.last_filter_debug = {}
        self.last_detected_peaks = []
        self.ecg_overlay_data = None
        self.ecg_overlay_column = None
        self.ecg_overlay_sampling_rate = None
        self.ecg_overlay_baseline_sec = 0.6
        self.ecg_overlay_baseline_poly = 3
        self.ecg_overlay_savgol_sec = 0.018
        self.ecg_overlay_savgol_poly = 3
        self.last_overlay_debug = {}

        self.top_layout = QHBoxLayout()
        self.top_layout.setSpacing(0)
        self.top_layout.addStretch()

        self.setStyleSheet("""
        QLabel {
            font-size: 14px;
        }""")

        self.toggle_theme = QCheckBox()
        self.toggle_theme.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 40px;
                height: 20px;
                border-radius: 10px;
                background-color: #ccc;
                position: relative;
            }}
            QCheckBox::indicator:checked {{
                background-color: #2d89ef;
                image: url("{DOT_BLACK_PATH}");
            }}
            QCheckBox::indicator:unchecked {{
                background-color: #ccc;
                image: url("{DOT_WHITE_PATH}");
            }}
        """)

        self.toggle_theme.stateChanged.connect(self.change_theme)

        self.theme_label = QLabel("Dark Mode")
        self.theme_label.setStyleSheet("font-size: 14px; padding-bottom: 1px;")

        self.top_layout.addWidget(self.toggle_theme, alignment=Qt.AlignRight)
        self.top_layout.addWidget(self.theme_label, alignment=Qt.AlignRight)
        self.layout.addLayout(self.top_layout)

        self.file_path_label = QLabel("No file selected")
        self.layout.addWidget(self.file_path_label, alignment=Qt.AlignLeft)

        self.start_layout = QHBoxLayout()

        self.file_analysis_button = QPushButton("File data analysis")
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

        self.real_time_analysis_button = QPushButton("Real-time monitoring")
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

        self.channel_label = QLabel("Signal channel")
        self.filters_defined_layout.addWidget(self.channel_label, alignment=Qt.AlignTop)

        self.channel_selector = QComboBox()
        self.channel_selector.currentTextChanged.connect(self.on_primary_channel_changed)
        self.filters_defined_layout.addWidget(self.channel_selector, alignment=Qt.AlignTop)

        self.reference_label = QLabel("Reference channel")
        self.filters_defined_layout.addWidget(self.reference_label, alignment=Qt.AlignTop)

        self.reference_selector = QComboBox()
        self.reference_selector.currentTextChanged.connect(self.on_reference_channel_changed)
        self.filters_defined_layout.addWidget(self.reference_selector, alignment=Qt.AlignTop)

        self.processing_profile_label = QLabel("Processing preset")
        self.filters_defined_layout.addWidget(self.processing_profile_label, alignment=Qt.AlignTop)

        self.processing_profile_selector = QComboBox()
        self.processing_profile_selector.addItems([
            "Auto",
            "MKG (0.5-120 Hz)",
            "ECG (5-45 Hz)",
            "Custom"
        ])
        self.processing_profile_selector.currentTextChanged.connect(self.on_processing_profile_changed)
        self.filters_defined_layout.addWidget(self.processing_profile_selector, alignment=Qt.AlignTop)

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

        self.reference_cancel_checkbox = QCheckBox("Reference cancel")
        self.reference_cancel_checkbox.stateChanged.connect(lambda: handle_filter_toggle(self, 'reference_cancel'))
        self.filters_defined_layout.addWidget(self.reference_cancel_checkbox, alignment=Qt.AlignTop)

        self.auto_notch_checkbox = QCheckBox("Auto notch")
        self.auto_notch_checkbox.setChecked(True)
        self.auto_notch_checkbox.stateChanged.connect(lambda: handle_filter_toggle(self, 'auto_notch'))
        self.filters_defined_layout.addWidget(self.auto_notch_checkbox, alignment=Qt.AlignTop)

        self.baseline_remove_checkbox = QCheckBox("Baseline removal")
        self.baseline_remove_checkbox.setChecked(True)
        self.baseline_remove_checkbox.stateChanged.connect(lambda: handle_filter_toggle(self, 'baseline'))
        self.filters_defined_layout.addWidget(self.baseline_remove_checkbox, alignment=Qt.AlignTop)

        self.savgol_smooth_checkbox = QCheckBox("Savgol smoothing")
        self.savgol_smooth_checkbox.setChecked(False)
        self.savgol_smooth_checkbox.stateChanged.connect(lambda: handle_filter_toggle(self, 'savgol'))
        self.filters_defined_layout.addWidget(self.savgol_smooth_checkbox, alignment=Qt.AlignTop)

        self.despike_filter = QCheckBox("Spike cleanup")
        self.despike_filter.stateChanged.connect(lambda: handle_filter_toggle(self, 'despike'))
        self.filters_defined_layout.addWidget(self.despike_filter, alignment=Qt.AlignTop)

        self.feature_toggle = QCheckBox("Beat markers")
        self.feature_toggle.stateChanged.connect(lambda: handle_filter_toggle(self, 'features'))
        self.filters_defined_layout.addWidget(self.feature_toggle, alignment=Qt.AlignTop)
        self.ecg_overlay_checkbox = QCheckBox("ECG overlay")
        self.ecg_overlay_checkbox.setChecked(False)
        self.ecg_overlay_checkbox.stateChanged.connect(lambda: handle_filter_toggle(self, 'ecg_overlay'))
        self.filters_defined_layout.addWidget(self.ecg_overlay_checkbox, alignment=Qt.AlignTop)

        self.custom_filters_layout = QVBoxLayout()

        self.custom_filter1_layout = QHBoxLayout()
        self.custom_filter_1_input = QLineEdit()
        self.custom_filter_1_input.setPlaceholderText("1-230Hz")
        self.custom_filter_1_input.setFixedWidth(100)
        self.custom_filter_1_validator = QIntValidator(1, 230, self)
        self.custom_filter_1_input.setValidator(self.custom_filter_1_validator)
        self.custom_filter_1_input.textChanged.connect(lambda: validate_custom_filter(self.custom_filter_1_input, self.custom_filter_1_apply))
        self.custom_filter1_layout.addWidget(self.custom_filter_1_input, alignment=Qt.AlignTop)

        self.custom_filter_1_apply = QCheckBox("Apply")
        self.custom_filter_1_apply.setEnabled(False)
        self.custom_filter_1_apply.stateChanged.connect(lambda: handle_filter_toggle(self, 'custom_filter_1'))
        self.custom_filter1_layout.addWidget(self.custom_filter_1_apply, alignment=Qt.AlignLeft)

        self.custom_filter2_layout = QHBoxLayout()
        self.custom_filter_2_input = QLineEdit()
        self.custom_filter_2_input.setPlaceholderText("1-230Hz")
        self.custom_filter_2_input.setFixedWidth(100)
        self.custom_filter_2_validator = QIntValidator(1, 230, self)
        self.custom_filter_2_input.setValidator(self.custom_filter_2_validator)
        self.custom_filter_2_input.textChanged.connect(lambda: validate_custom_filter(self.custom_filter_2_input, self.custom_filter_2_apply))
        self.custom_filter2_layout.addWidget(self.custom_filter_2_input, alignment=Qt.AlignTop)

        self.custom_filter_2_apply = QCheckBox("Apply")
        self.custom_filter_2_apply.setEnabled(False)
        self.custom_filter_2_apply.stateChanged.connect(lambda: handle_filter_toggle(self, 'custom_filter_2'))
        self.custom_filter2_layout.addWidget(self.custom_filter_2_apply, alignment=Qt.AlignLeft)

        self.bandpass_layout = QHBoxLayout()
        self.bandpass_slider = QLabeledDoubleRangeSlider(Qt.Horizontal)
        self.bandpass_slider.setRange(0.5, 230)
        self.bandpass_slider.setValue((4, 90))
        self.bandpass_slider.setFixedWidth(100)
        self.bandpass_slider.setSingleStep(0.5)
        self.bandpass_slider.setDecimals(1)

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
        self.channel_label.hide()
        self.channel_selector.hide()
        self.reference_label.hide()
        self.reference_selector.hide()
        self.processing_profile_label.hide()
        self.processing_profile_selector.hide()
        self.lowpass_filter.hide()
        self.highpass_filter.hide()
        self.filter_50hz.hide()
        self.filter_100hz.hide()
        self.filter_150hz.hide()
        self.reference_cancel_checkbox.hide()
        self.auto_notch_checkbox.hide()
        self.ecg_overlay_checkbox.hide()
        self.baseline_remove_checkbox.hide()
        self.savgol_smooth_checkbox.hide()
        self.despike_filter.hide()
        self.feature_toggle.hide()
        self.custom_filter_1_input.hide()
        self.custom_filter_1_apply.hide()
        self.custom_filter_2_input.hide()
        self.custom_filter_2_apply.hide()

        self.range_and_filters_layout = QHBoxLayout()
        self.range_and_filters_layout.addLayout(self.range_layout)
        self.range_and_filters_layout.addLayout(self.filters_defined_layout)
        self.range_and_filters_layout.addLayout(self.custom_filters_layout)

        switch_style = f"""
            QCheckBox::indicator {{
                width: 40px;
                height: 20px;
                border-radius: 10px;
                background-color: #ccc;
                position: relative;
            }}
            QCheckBox::indicator:checked {{
                background-color: #2d89ef;
                image: url("{DOT_BLACK_PATH}");
            }}
            QCheckBox::indicator:unchecked {{
                background-color: #ccc;
                image: url("{DOT_WHITE_PATH}");
            }}
        """

        self.lowpass_filter.setStyleSheet(switch_style)
        self.highpass_filter.setStyleSheet(switch_style)
        self.filter_50hz.setStyleSheet(switch_style)
        self.filter_100hz.setStyleSheet(switch_style)
        self.filter_150hz.setStyleSheet(switch_style)
        self.reference_cancel_checkbox.setStyleSheet(switch_style)
        self.auto_notch_checkbox.setStyleSheet(switch_style)
        self.baseline_remove_checkbox.setStyleSheet(switch_style)
        self.savgol_smooth_checkbox.setStyleSheet(switch_style)
        self.despike_filter.setStyleSheet(switch_style)
        self.feature_toggle.setStyleSheet(switch_style)
        self.ecg_overlay_checkbox.setStyleSheet(switch_style)
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

        self.feature_summary_label = QLabel("")
        self.feature_summary_label.setStyleSheet("font-size: 12px; color: #2d89ef;")
        self.feature_summary_label.hide()
        self.layout.addWidget(self.feature_summary_label, alignment=Qt.AlignLeft)

    def start_file_analysis(self):
        load_and_plot_file(self)

    def start_real_time_analysis(self):
        if not hasattr(self, 'real_time_window') or self.real_time_window is None:
            self.real_time_window = RealTimePlotWindow()
            self.real_time_window.closed.connect(self.reset_real_time_window)
            self.real_time_window.show()
        else:
            print("The real-time analysis window is now open")

    def reset_real_time_window(self):
        print("Resetting the real_time_window flag")
        self.real_time_window = None
        import gc
        gc.collect()

    def show_controls(self):
        show_controls(self)

    def reset_controls_to_default(self):
        self.pan_slider.setEnabled(False)

        self.bandpass_slider.setValue((3, 80))
        self.bandpass_apply.setChecked(False)

        self.lowpass_filter.setChecked(False)
        self.highpass_filter.setChecked(False)
        self.filter_50hz.setChecked(False)
        self.filter_100hz.setChecked(False)
        self.filter_150hz.setChecked(False)
        self.custom_filter_1_input.clear()
        self.custom_filter_1_apply.setChecked(False)
        self.custom_filter_2_input.clear()
        self.custom_filter_2_apply.setChecked(False)
        self.reference_cancel_checkbox.setChecked(False)
        self.auto_notch_checkbox.setChecked(True)
        self.baseline_remove_checkbox.setChecked(True)
        self.savgol_smooth_checkbox.setChecked(False)
        self.despike_filter.setChecked(False)
        self.feature_toggle.setChecked(False)
        self.ecg_overlay_checkbox.setChecked(False)
        self.ecg_overlay_checkbox.setVisible(False)
        self.ecg_overlay_checkbox.setEnabled(False)
        self.ecg_overlay_data = None
        self.ecg_overlay_column = None
        self.ecg_overlay_sampling_rate = None
        self.last_overlay_debug = {}
        self.processing_profile_selector.setCurrentIndex(0)
        self.processing_profile_selector.setEnabled(False)
        self.auto_notch_checkbox.setEnabled(False)
        self.baseline_remove_checkbox.setEnabled(False)
        self.savgol_smooth_checkbox.setEnabled(False)
        self.processing_profile = "Auto"
        self.last_detected_profile = None

        self.time_from_input.clear()
        self.time_from_input.setStyleSheet("border: 1px solid #ccc; border-radius: 10px;")
        self.error_from_label.clear()
        self.error_from_label.hide()

        self.time_to_input.clear()
        self.time_to_input.setStyleSheet("border: 1px solid #ccc; border-radius: 10px;")
        self.error_to_label.clear()
        self.error_to_label.hide()

        self.file_name_input.clear()
        self.save_txt.setChecked(False)
        self.save_tsv.setChecked(False)
        self.save_xlsx.setChecked(False)

        self.current_time_from = None
        self.current_time_to = None
        self.data = None
        self.available_channels = []
        self.primary_channel = None
        self.reference_channel = None
        self.channel_selector.clear()
        self.channel_selector.setEnabled(False)
        self.reference_selector.clear()
        self.reference_selector.setEnabled(False)
        self.reference_label.setEnabled(False)
        self.reference_cancel_checkbox.setEnabled(False)
        self.feature_summary_label.hide()
        self.feature_summary_label.clear()

    def configure_channel_selectors(self, channels):
        self.available_channels = channels or []
        self.channel_selector.blockSignals(True)
        self.reference_selector.blockSignals(True)

        self.channel_selector.clear()
        self.reference_selector.clear()

        for channel in self.available_channels:
            self.channel_selector.addItem(channel)
            self.reference_selector.addItem(channel)

        if self.available_channels:
            target_primary = self.primary_channel if self.primary_channel in self.available_channels else self.available_channels[0]
            self.primary_channel = target_primary
            primary_index = self.channel_selector.findText(target_primary)
            if primary_index >= 0:
                self.channel_selector.setCurrentIndex(primary_index)

        enable_reference = len(self.available_channels) > 1
        self.channel_selector.setEnabled(bool(self.available_channels))
        self.reference_selector.setEnabled(enable_reference)
        self.reference_label.setEnabled(enable_reference)
        self.reference_cancel_checkbox.setEnabled(enable_reference)
        self.auto_notch_checkbox.setEnabled(bool(self.available_channels))
        self.processing_profile_selector.setEnabled(bool(self.available_channels))
        self.baseline_remove_checkbox.setEnabled(bool(self.available_channels))
        self.savgol_smooth_checkbox.setEnabled(bool(self.available_channels))

        if enable_reference:
            if self.reference_channel not in self.available_channels or self.reference_channel == self.primary_channel:
                available_refs = [ch for ch in self.available_channels if ch != self.primary_channel]
                self.reference_channel = available_refs[0] if available_refs else None
            if self.reference_channel:
                ref_index = self.reference_selector.findText(self.reference_channel)
                if ref_index >= 0:
                    self.reference_selector.setCurrentIndex(ref_index)
        else:
            self.reference_channel = None
            self.reference_cancel_checkbox.setChecked(False)

        self.channel_selector.blockSignals(False)
        self.reference_selector.blockSignals(False)

        selection = self.processing_profile_selector.currentText()
        if selection != "Custom":
            self.apply_processing_profile_defaults(selection)
        elif self.data is not None:
            refresh_plot(self)

    def on_primary_channel_changed(self, channel_name):
        if not channel_name:
            return
        self.primary_channel = channel_name
        if self.reference_channel == self.primary_channel:
            self.reference_channel = None
            self.reference_cancel_checkbox.setChecked(False)
        if self.processing_profile_selector.currentText() != "Custom":
            self.apply_processing_profile_defaults(self.processing_profile_selector.currentText())
        elif self.data is not None:
            refresh_plot(self)

    def on_reference_channel_changed(self, channel_name):
        if not channel_name or channel_name == self.primary_channel:
            self.reference_channel = None
            if self.reference_cancel_checkbox.isChecked():
                self.reference_cancel_checkbox.setChecked(False)
        else:
            self.reference_channel = channel_name
        if self.data is not None:
            refresh_plot(self)

    def on_processing_profile_changed(self, text):
        if text == "Custom":
            self.processing_profile = "Custom"
            return
        self.apply_processing_profile_defaults(text)

    def get_bandpass_upper_limit(self):
        fs = self.sampling_rate or getattr(self, 'last_sampling_rate', 480.0)
        if not fs or fs <= 0:
            fs = 480.0
        return min(230.0, max(5.0, 0.49 * fs))

    def set_bandpass_slider_value(self, low, high):
        previous = self.bandpass_slider.blockSignals(True)
        self.bandpass_slider.setValue((low, high))
        validate_bandpass_values(self)
        self.bandpass_slider.blockSignals(previous)

    @staticmethod
    def set_checkbox_state(checkbox, checked):
        if checkbox is None:
            return
        previous = checkbox.blockSignals(True)
        checkbox.setChecked(checked)
        checkbox.blockSignals(previous)

    def detect_profile_for_channel(self):
        if not self.primary_channel or self.data is None or self.primary_channel not in self.data.columns:
            return "MKG (0.5-120 Hz)"
        name = str(self.primary_channel).lower()
        series = self.data[self.primary_channel]
        if "ecg" in name or "reference" in name or "ard" in name:
            return "ECG (5-45 Hz)"
        if series.abs().median() > 5 or series.abs().max() > 30:
            return "ECG (5-45 Hz)"
        return "MKG (0.5-120 Hz)"

    def apply_processing_profile_defaults(self, profile_option):
        if profile_option == "Custom":
            self.processing_profile = "Custom"
            return

        target = profile_option
        if profile_option.startswith("Auto"):
            target = self.detect_profile_for_channel()
        self.last_detected_profile = target
        upper = self.get_bandpass_upper_limit()

        if target.startswith("ECG"):
            low, high = 5.0, min(45.0, upper)
            self.baseline_window_sec = 0.6
            self.savgol_window_sec = 0.018
            self.savgol_polyorder = 3
            self.set_checkbox_state(self.baseline_remove_checkbox, True)
            self.set_checkbox_state(self.savgol_smooth_checkbox, True)
        elif target.startswith("MKG"):
            low, high = 0.5, min(120.0, upper)
            self.baseline_window_sec = 0.8
            self.savgol_window_sec = 0.025
            self.savgol_polyorder = 3
            self.set_checkbox_state(self.baseline_remove_checkbox, True)
            self.set_checkbox_state(self.savgol_smooth_checkbox, False)
        else:
            self.processing_profile = "Custom"
            return

        self.processing_profile = target
        self.set_checkbox_state(self.auto_notch_checkbox, True)

        self.set_checkbox_state(self.lowpass_filter, False)
        self.set_checkbox_state(self.highpass_filter, False)
        self.set_checkbox_state(self.bandpass_apply, True)
        self.set_bandpass_slider_value(low, high)

        if self.data is not None:
            refresh_plot(self)

    def update_feature_summary(self, features):
        self.last_feature_summary = features or {}
        parts = []

        if features:
            heart_rate = features.get("heart_rate_bpm")
            if heart_rate:
                parts.append(f"HR {heart_rate:.1f} bpm")
            rr_mean = features.get("rr_mean")
            if rr_mean:
                parts.append(f"RR mean {rr_mean:.3f}s")
            rr_std = features.get("rr_std")
            if rr_std:
                parts.append(f"RR std {rr_std:.3f}s")

        line_info = getattr(self, "last_filter_debug", None)
        if isinstance(line_info, dict):
            power_info = line_info.get("line_power", {})
            pre = power_info.get("pre", {}) if isinstance(power_info, dict) else {}
            post = power_info.get("post", {}) if isinstance(power_info, dict) else {}
            for freq in sorted(pre.keys()):
                if freq not in post:
                    continue
                pre_val = pre.get(freq, 0.0)
                post_val = post.get(freq, 0.0)
                if pre_val <= 0:
                    continue
                ratio = pre_val / max(post_val, 1e-12)
                label = f"{int(round(freq))}Hz"
                if ratio >= 1.05:
                    parts.append(f"{label} x{ratio:.1f}")
                elif ratio > 0:
                    parts.append(f"{label} x{ratio:.2f}")
            auto_notches = line_info.get("auto_notches")
            if auto_notches:
                parts.append("Auto notch " + ", ".join(f"{freq:.1f}Hz" for freq in auto_notches))

        overlay_info = getattr(self, "last_overlay_debug", None)
        if isinstance(overlay_info, dict):
            power_info = overlay_info.get("line_power", {})
            pre = power_info.get("pre", {}) if isinstance(power_info, dict) else {}
            post = power_info.get("post", {}) if isinstance(power_info, dict) else {}
            for freq in sorted(pre.keys()):
                if freq not in post:
                    continue
                pre_val = pre.get(freq, 0.0)
                post_val = post.get(freq, 0.0)
                if pre_val <= 0:
                    continue
                ratio = pre_val / max(post_val, 1e-12)
                label = f"ECG {int(round(freq))}Hz"
                if ratio >= 1.05:
                    parts.append(f"{label} x{ratio:.1f}")
                elif ratio > 0:
                    parts.append(f"{label} x{ratio:.2f}")
        if parts:
            self.feature_summary_label.setText(" | ".join(parts))
            self.feature_summary_label.show()
        else:
            self.feature_summary_label.clear()
            self.feature_summary_label.hide()

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
                QMessageBox {
                    background-color: #2c2c2c;
                    color: white;
                    border-radius: 10px;
                }
                QMessageBox QLabel {
                    color: white;
                    font-size: 14px;
                    padding-top: 5px;
                }
                QMessageBox QPushButton {
                    background-color: #555;
                    color: white;
                    border-radius: 15px;
                    padding: 10px 18px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #777;
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
                QMessageBox {
                    background-color: white;
                    color: black;
                    border-radius: 10px;
                }
                QMessageBox QLabel {
                    color: black;
                    font-size: 14px;
                    padding-top: 5px;
                }
                QMessageBox QPushButton {
                    background-color: #2d89ef;
                    color: white;
                    border-radius: 15px;
                    padding: 10px 18px;
                }
                QMessageBox QPushButton:hover {
                    background-color: #1e70c1;
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
