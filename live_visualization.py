import os
import sys
from PyQt5.QtGui import QIntValidator, QIcon
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QFileDialog, QPushButton, QHBoxLayout, QCheckBox, QLabel, \
    QSizePolicy, QFrame, QLineEdit
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject, QThreadPool, QEvent
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import threading
import time
import subprocess
import datetime
import queue
import tio
import slip
import serial
from backend import validate_custom_filter, state_change, detect_sensor_port, IMAGES_DIR, DOT_BLACK_PATH, DOT_WHITE_PATH
from signal_processing import FilterSettings, apply_filter_pipeline, DEFAULT_FS
from collections import deque

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DEVCON_PATH = os.path.join(BASE_DIR, "devcon.exe").replace("\\", "/")


class CustomTIOSession(tio.TIOSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.recv_buffer = bytearray()

    def recv_slip_packet(self):
        while self.alive and self.serial.is_open:
            try:
                data = self.serial.read(self.serial.in_waiting or 1)
            except serial.SerialException as e:
                raise IOError(f"serial error: {e}")
            else:
                if data:
                    self.buffer.extend(data)
                    if len(self.buffer) > 1000000:
                        self.warn_overload()
                    while slip.SLIP_END_CHAR in self.buffer:
                        packet, self.buffer = self.buffer.split(slip.SLIP_END_CHAR, 1)
                        try:
                            return slip.decode(packet)
                        except slip.SLIPEncodingError as error:
                            self.logger.debug(error)
                            return b""


class RealTimePlotWindow(QMainWindow):
    closed = pyqtSignal()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange or event.type() == QEvent.ActivationChange:
            state_change(self)
        super().changeEvent(event)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Data Plot")
        self.setWindowIcon(QIcon(os.path.join(IMAGES_DIR, "Icon.png")))
        self.resize(1500, 800)
        self.setMinimumSize(1500, 800)
        self.setWindowFlags(self.windowFlags() | Qt.Window)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(5)

        self.top_layout = QVBoxLayout()
        self.top_layout.setAlignment(Qt.AlignTop)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(5)

        self.toggle_theme = QCheckBox()
        self.toggle_theme.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 40px;
                height: 20px;
                border-radius: 10px;
                background-color: #ccc;
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

        self.theme_label = QLabel("Dark mode")
        self.theme_label.setStyleSheet("font-size: 14px; padding: 0px;")

        self.dark_mode_layout = QHBoxLayout()
        self.dark_mode_layout.setContentsMargins(0, 0, 0, 20)
        self.dark_mode_layout.setSpacing(0)
        self.dark_mode_layout.addStretch()
        self.dark_mode_layout.addWidget(self.toggle_theme, alignment=Qt.AlignRight)
        self.dark_mode_layout.addWidget(self.theme_label, alignment=Qt.AlignRight)
        self.top_layout.addLayout(self.dark_mode_layout)

        self.filters_layout = QHBoxLayout()

        self.filters_label = QLabel("Filters:")
        self.filters_label.setStyleSheet("font-size: 16px; padding: 0px;")
        self.filters_layout.addWidget(self.filters_label)
        self.filters_layout.addStretch()

        self.lowpass_filter = QCheckBox("Lowpass")
        self.lowpass_filter.clicked.connect(self.toggle_lowpass)
        self.filters_layout.addWidget(self.lowpass_filter)
        self.filters_layout.addStretch()

        self.highpass_filter = QCheckBox("Highpass")
        self.highpass_filter.clicked.connect(self.toggle_highpass)
        self.filters_layout.addWidget(self.highpass_filter)
        self.filters_layout.addStretch()

        self.notch_filter = QCheckBox("50 Hz")
        self.notch_filter.clicked.connect(self.toggle_notch)
        self.filters_layout.addWidget(self.notch_filter)
        self.filters_layout.addStretch()

        self.baseline_filter = QCheckBox("Baseline")
        self.baseline_filter.setChecked(True)
        self.baseline_filter.clicked.connect(self.toggle_baseline)
        self.filters_layout.addWidget(self.baseline_filter)
        self.filters_layout.addStretch()

        self.savgol_filter = QCheckBox("Smooth")
        self.savgol_filter.clicked.connect(self.toggle_savgol)
        self.filters_layout.addWidget(self.savgol_filter)
        self.filters_layout.addStretch()

        self.custom_filter_layout = QHBoxLayout()
        self.custom_filter_input = QLineEdit()
        self.custom_filter_input.setPlaceholderText("1-230Hz")
        self.custom_filter_input.setFixedWidth(100)
        self.custom_filter_validator = QIntValidator(1, 230, self)
        self.custom_filter_input.setValidator(self.custom_filter_validator)
        self.custom_filter_input.textChanged.connect(
            lambda: validate_custom_filter(self.custom_filter_input, self.custom_filter_apply))
        self.custom_filter_layout.addWidget(self.custom_filter_input, alignment=Qt.AlignRight)

        self.custom_filter_apply = QCheckBox("Apply")
        self.custom_filter_apply.setEnabled(False)
        self.custom_filter_apply.clicked.connect(self.toggle_custom)
        self.custom_filter_layout.addWidget(self.custom_filter_apply, alignment=Qt.AlignRight)
        self.filters_layout.addLayout(self.custom_filter_layout)

        self.top_layout.addLayout(self.filters_layout)

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
        self.notch_filter.setStyleSheet(switch_style)
        self.baseline_filter.setStyleSheet(switch_style)
        self.savgol_filter.setStyleSheet(switch_style)
        self.custom_filter_apply.setStyleSheet(switch_style)

        self.lowpass_enabled = False
        self.highpass_enabled = False
        self.notch_enabled = False
        self.custom_enabled = False
        self.lowpass_cutoff = 120.0
        self.highpass_cutoff = 0.5
        self.custom_notch_freq = None
        self.baseline_enabled = True
        self.savgol_enabled = False
        self.baseline_window_sec = 0.6
        self.baseline_polyorder = 3
        self.savgol_window_sec = 0.02
        self.savgol_polyorder = 3

        self.canvas_frame = QFrame(self.central_widget)
        self.canvas_frame.setContentsMargins(0, 0, 0, 0)

        self.canvas = RealTimePlotCanvas()
        self.canvas.parent_window = self

        self.canvas_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.canvas_frame_layout = QVBoxLayout(self.canvas_frame)
        self.canvas_frame_layout.setContentsMargins(20, 20, 20, 20)
        self.canvas_frame_layout.setSpacing(10)
        self.canvas_frame_layout.addWidget(self.canvas)

        self.top_layout.addWidget(self.canvas_frame)
        self.layout.addLayout(self.top_layout)

        self.button_layout = QHBoxLayout()
        self.start_recording_button = QPushButton("Start recording")
        self.stop_recording_button = QPushButton("Stop recording")

        button_style = """
            QPushButton {
                background-color: #2d89ef;
                color: white;
                border-radius: 10px;
                padding: 10px 20px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QPushButton:hover:!disabled {
                background-color: #1e70c1;
            }
        """
        self.start_recording_button.setStyleSheet(button_style)
        self.stop_recording_button.setStyleSheet(button_style)

        self.start_recording_button.clicked.connect(self.start_recording)
        self.stop_recording_button.clicked.connect(self.stop_recording)
        self.stop_recording_button.setEnabled(False)

        self.button_layout.addWidget(self.start_recording_button)
        self.button_layout.addWidget(self.stop_recording_button)
        self.layout.addLayout(self.button_layout)
        print("Call self.canvas.start_data_loop()")
        self.canvas.start_data_loop()
        self.change_theme(0)

    def toggle_lowpass(self):
        self.lowpass_enabled = self.lowpass_filter.isChecked()
        print(f"Lowpass: {self.lowpass_enabled}")

    def toggle_highpass(self):
        self.highpass_enabled = self.highpass_filter.isChecked()
        print(f"Highpass: {self.highpass_enabled}")

    def toggle_notch(self):
        self.notch_enabled = self.notch_filter.isChecked()
        print(f"50 Hz: {self.notch_enabled}")

    def toggle_custom(self):
        self.custom_enabled = self.custom_filter_apply.isChecked()
        self.custom_notch_freq = None
        if self.custom_enabled:
            text = self.custom_filter_input.text().strip()
            if text.isdigit():
                self.custom_notch_freq = float(text)
        print(f"Custom filter: {self.custom_enabled} ({self.custom_notch_freq})")

    def toggle_baseline(self):
        self.baseline_enabled = self.baseline_filter.isChecked()
        print(f"Baseline removal: {self.baseline_enabled}")

    def toggle_savgol(self):
        self.savgol_enabled = self.savgol_filter.isChecked()
        print(f"Savgol smoothing: {self.savgol_enabled}")

    def change_theme(self, state):
        if state == 2:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2c2c2c;
                }
                QLabel, QCheckBox, QPushButton {
                    color: #f0f0f0;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #555;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #333;
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
            self.canvas.set_dark_mode(True)
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f0f0f0;
                }
                QLabel, QCheckBox, QPushButton {
                    color: #333;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #2d89ef;
                    color: white;
                    border-radius: 10px;
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
            """)
            if self.canvas_frame:
                self.canvas_frame.setStyleSheet("""
                    QFrame {
                        border: 1px solid #2d89ef;
                        border-radius: 15px;
                        background-color: white;
                    }
                """)
            self.canvas.set_dark_mode(False)

    def start_recording(self):
        self.data_recording = True
        self.record_start_time = datetime.datetime.now()
        self.recorded_data = []
        self.start_recording_button.setEnabled(False)
        self.stop_recording_button.setEnabled(True)
        print(f"Data recording has begun: {self.data_recording}")

    def stop_recording(self):
        self.data_recording = False
        self.start_recording_button.setEnabled(True)
        self.stop_recording_button.setEnabled(False)

        if self.recorded_data:
            default_filename = self.record_start_time.strftime("%Y-%m-%d_%H-%M-%S")
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save the file", default_filename, "Pliki CSV (*.csv);;Wszystkie pliki (*)", options=options
            )
            if file_path:
                with open(file_path, "w") as file:
                    file.write("Time, Value\n")
                    for timestamp, value in self.recorded_data:
                        file.write(f"{timestamp},{value}\n")
                print(f"The data was recorded in a file: {file_path}")
        else:
            print("No data was recorded")

    def closeEvent(self, event):
        print("Zamykam RealTimePlotWindow.")
        self.canvas.stop_data_loop()
        try:
            if self.canvas.session:
                self.canvas.session.close()
            reset_com_port()
        except Exception as e:
            print(f"COM port reset error: {e}")
        self.closed.emit()
        super().closeEvent(event)


class RealTimePlotCanvas(FigureCanvas):
    data_received = pyqtSignal(float)

    def __init__(self):
        super().__init__()

        self.session = None
        self.data_thread = None

        self.parent_window = None
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.xlim = 200
        self.n = np.linspace(0, self.xlim - 1, self.xlim)
        self.y = np.zeros(self.xlim)

        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.ax1 = self.fig.add_subplot(111)
        self.ax1.set_xlim(0, self.xlim - 1)
        self.ax1.set_xlabel('Index')
        self.ax1.set_ylabel('Sensor Value')

        self.line1, = self.ax1.plot([], [], 'b-', label='Sensor Data')
        self.ax1.legend()

        super().__init__(self.fig)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(10)

        self.addedData = []
        self.running = False
        self.setAttribute(Qt.WA_DeleteOnClose, True)

        self.sample_rate = DEFAULT_FS
        self.buffer = deque(maxlen=2000)
        self.delay = 50
        self.threadpool = QThreadPool()
        print("RealTimePlotCanvas.__init__ called")

    def add_data(self, value):
        print(f"add_data called with the value: {value}")
        self.addedData.append(value)

    def update_plot(self):
        try:
            if len(self.buffer) < self.delay + 10:
                return

            raw_data = np.array(self.buffer, dtype=float)
            if raw_data.size < self.delay + 1:
                return

            custom_notches = ()
            if self.parent_window.custom_enabled and self.parent_window.custom_notch_freq:
                custom_notches = (self.parent_window.custom_notch_freq,)

            settings = FilterSettings(
                fs=self.sample_rate,
                use_highpass=self.parent_window.highpass_enabled,
                highpass_cutoff=self.parent_window.highpass_cutoff,
                use_lowpass=self.parent_window.lowpass_enabled,
                lowpass_cutoff=self.parent_window.lowpass_cutoff,
                notch_freqs=(50.0,) if self.parent_window.notch_enabled else (),
                custom_notch_freqs=custom_notches,
                use_baseline=self.parent_window.baseline_enabled,
                baseline_window_sec=self.parent_window.baseline_window_sec,
                baseline_polyorder=self.parent_window.baseline_polyorder,
                use_savgol_smooth=self.parent_window.savgol_enabled,
                savgol_window_sec=self.parent_window.savgol_window_sec,
                auto_notch=True,
                savgol_polyorder=self.parent_window.savgol_polyorder,
            )

            y_filtered, _ = apply_filter_pipeline(raw_data, settings)

            display_value = y_filtered[-self.delay]

            self.y = np.roll(self.y, -1)
            self.y[-1] = display_value

            if self.parent_window and hasattr(self.parent_window,
                                              'data_recording') and self.parent_window.data_recording:
                timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")
                self.parent_window.recorded_data.append((timestamp, display_value))

            y_min, y_max = self.y.min(), self.y.max()
            if np.isnan(y_min) or np.isnan(y_max) or np.isinf(y_min) or np.isinf(y_max):
                self.ax1.set_ylim(-1, 1)
            else:
                data_range = y_max - y_min
                margin = (data_range / 2) if data_range != 0 else 1
                self.ax1.set_ylim(y_min - margin, y_max + margin)

            self.line1.set_data(np.arange(self.xlim), self.y)
            self.ax1.draw_artist(self.ax1.patch)
            self.ax1.draw_artist(self.line1)
            self.blit(self.ax1.bbox)

        except Exception as e:
            print(f"Error in update_plot: {e}")

    def start_data_loop(self):
        print("start_data_loop called")
        self.running = True
        self.data_thread = threading.Thread(target=self.data_loop, daemon=True)
        self.data_thread.start()
        print("Data_thread running")

    def stop_data_loop(self):
        self.running = False

        if self.data_thread is not None and self.data_thread.is_alive():
            self.data_thread.join(timeout=2)

        if self.session:
            self.session.alive = False
            time.sleep(1)
            self.session.close()
            try:
                if self.session.serial.is_open:
                    self.session.serial.close()
            except Exception as e:
                print(f"Serial close error: {e}")

    def data_loop(self):
        print("data_loop called")
        try:
            sensor_port = detect_sensor_port()
            self.session = CustomTIOSession(url=sensor_port, verbose=False, specialize=False)
            if not self.session:
                print("Failed to initialise sensor.")
                return

            print("Sensor initialised")
            self.session.specialize(connectingMessage=True, stateCache=False)
            wait_start_time = time.time()
            while not self.session.protocol.streams:
                time.sleep(0.1)
                if time.time() - wait_start_time > 5:
                    print("Stream info not received in time.")
                    return

            self.session.rpc_val("gradient.data.decimation", tio.UINT32_T, 1)
            print("Stream ready. Reading data...")

            self.running = True
            columns = self.session.protocol.columns
            if "gradient" not in columns:
                print("gradient not in columns:", columns)
                return
            gradient_index = columns.index("gradient")

            while self.running:
                try:
                    decoded_packet = self.session.pub_queue.get(timeout=1)
                    if decoded_packet["type"] != tio.TL_PTYPE_STREAM0:
                        continue

                    result = self.session.protocol.stream_data(decoded_packet, timeaxis=True)
                    if not isinstance(result, tuple) or len(result) < 2:
                        continue
                    timestamp, values = result

                    if len(values) <= gradient_index:
                        continue
                    gradient_value = values[gradient_index]

                    self.buffer.append(gradient_value)

                except queue.Empty:
                    pass
                except Exception as e:
                    print(f"Error in data_loop: {e}")
        finally:
            if self.session:
                self.session.close()

    def set_dark_mode(self, enabled):
        if enabled:
            self.ax1.set_facecolor('#2c2c2c')
            self.fig.patch.set_facecolor('#2c2c2c')
            self.ax1.spines['bottom'].set_color('white')
            self.ax1.spines['left'].set_color('white')
            self.ax1.tick_params(axis='x', colors='white')
            self.ax1.tick_params(axis='y', colors='white')
            self.ax1.xaxis.label.set_color('white')
            self.ax1.yaxis.label.set_color('white')
            self.ax1.title.set_color('white')
            self.line1.set_color('cyan')
        else:
            self.ax1.set_facecolor('white')
            self.fig.patch.set_facecolor('white')
            self.ax1.spines['bottom'].set_color('black')
            self.ax1.spines['left'].set_color('black')
            self.ax1.tick_params(axis='x', colors='black')
            self.ax1.tick_params(axis='y', colors='black')
            self.ax1.xaxis.label.set_color('black')
            self.ax1.yaxis.label.set_color('black')
            self.ax1.title.set_color('black')
            self.line1.set_color('blue')

        self.draw()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.figure.tight_layout()
        self.draw()


def reset_com_port():
    device_id = "USB\\VID_0483&PID_5740\\OMG16"
    try:
        print("Attempting COM port reset via devcon...")
        subprocess.run([DEVCON_PATH, "restart", device_id], check=True)
        print("COM port reset via devcon completed.")
    except subprocess.CalledProcessError as e:
        print(f"Device reset error: {e}")