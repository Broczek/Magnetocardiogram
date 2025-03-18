import os
import queue

from PyQt5.QtGui import QIntValidator, QIcon
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QFileDialog, QPushButton, QHBoxLayout, QCheckBox, QLabel, \
    QSizePolicy, QFrame, QLineEdit
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject, QThreadPool, QEvent
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import threading
import serial
import time
import subprocess
import datetime
import tio
import serial
from tio import TIOProtocol, TL_PTYPE_STREAM0
import slip
from slip import decode
from queue import Queue
from initialization import DeviceManual
from backend import lowpass_filter_live, highpass_filter_live, notch_filter, validate_custom_filter, state_change, IMAGES_DIR, DOT_BLACK_PATH, DOT_WHITE_PATH


class FilterWorkerSignals(QObject):
    result = pyqtSignal(object)
    error = pyqtSignal(object)


class TLRPCException(Exception):
    pass


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

        self.theme_label = QLabel("Tryb ciemny")
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

        self.custom_filter_layout = QHBoxLayout()
        self.custom_filter_input = QLineEdit()
        self.custom_filter_input.setPlaceholderText("1-999Hz")
        self.custom_filter_input.setFixedWidth(100)
        self.custom_filter_validator = QIntValidator(1, 999, self)
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
        self.custom_filter_apply.setStyleSheet(switch_style)

        self.lowpass_enabled = False
        self.highpass_enabled = False
        self.notch_enabled = False
        self.custom_enabled = False

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
        self.start_recording_button = QPushButton("Rozpocznij rejestrację")
        self.stop_recording_button = QPushButton("Zatrzymaj rejestrację")
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
        print("Wywołuję self.canvas.start_data_loop()")
        self.canvas.start_data_loop()
        self.change_theme(0)

    def toggle_lowpass(self):
        self.lowpass_enabled = self.lowpass_filter.isChecked()
        print(f"Filtr dolnoprzepustowy: {self.lowpass_enabled}")

    def toggle_highpass(self):
        self.highpass_enabled = self.highpass_filter.isChecked()
        print(f"Filtr górnoprzepustowy: {self.highpass_enabled}")

    def toggle_notch(self):
        self.notch_enabled = self.notch_filter.isChecked()
        print(f"Filtr 50 Hz: {self.notch_enabled}")

    def toggle_custom(self):
        self.custom_enabled = self.custom_filter_apply.isChecked()
        print(f"Filtr własny: {self.custom_enabled}")

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
        print(f"Rozpoczęto rejestrację danych: {self.data_recording}")

    def stop_recording(self):
        self.data_recording = False
        self.start_recording_button.setEnabled(True)
        self.stop_recording_button.setEnabled(False)

        if self.recorded_data:
            default_filename = self.record_start_time.strftime("%Y-%m-%d_%H-%M-%S")
            options = QFileDialog.Options()
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Zapisz plik", default_filename, "Pliki CSV (*.csv);;Wszystkie pliki (*)", options=options
            )
            if file_path:
                with open(file_path, "w") as file:
                    file.write("Czas, Wartość\n")
                    for timestamp, value in self.recorded_data:
                        file.write(f"{timestamp},{value}\n")
                print(f"Dane zapisano w pliku: {file_path}")
        else:
            print("Nie zarejestrowano żadnych danych.")

    def closeEvent(self, event):
        print("Zamykam RealTimePlotWindow.")
        self.canvas.stop_data_loop()
        try:
            devcon_path = r"C:\Program Files (x86)\Windows Kits\10\Tools\10.0.26100.0\x64\devcon.exe"
            device_id = "USB\\VID_0483&PID_5740"
            reset_com_port(devcon_path, device_id)
        except Exception as e:
            print(f"Błąd resetowania portu COM: {e}")
        self.closed.emit()
        super().closeEvent(event)


class RealTimePlotCanvas(FigureCanvas):
    data_received = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.protocol = TIOProtocol()
        self.data_thread = None

        self.parent_window = None
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.destroyed.connect(self.on_destroyed)
        self.xlim = 800
        self.n = np.linspace(0, self.xlim - 1, self.xlim)
        self.y = np.zeros(self.xlim)
        self.fig = Figure(figsize=(5, 5), dpi=100)
        self.ax1 = self.fig.add_subplot(111)
        self.ax1.set_xlim(0, self.xlim - 1)
        self.ax1.set_ylim(-900, -600)
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

        self.sample_rate = 480
        self.threadpool = QThreadPool()
        self.filter_queue = queue.Queue()
        self.filter_thread = threading.Thread(target=self.filter_loop, daemon=True)
        self.filter_thread.start()
        print("RealTimePlotCanvas.__init__ wywołane")

    def on_destroyed(self):
        print("RealTimePlotWindow zostało zniszczone.")

    def add_data(self, value):
        print(f"add_data wywołane z wartością: {value}")
        self.addedData.append(value)

    def update_plot(self):
        try:
            while self.addedData:
                value = self.addedData.pop(0)
                self.y = np.roll(self.y, -1)
                self.y[-1] = value

                if self.parent_window and hasattr(self.parent_window,
                                                  'data_recording') and self.parent_window.data_recording:
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")
                    self.parent_window.recorded_data.append((timestamp, value))
                    print(f"Dodano dane: {timestamp}, {value}")

            y_min, y_max = self.y.min(), self.y.max()
            if np.isnan(y_min) or np.isnan(y_max) or np.isinf(y_min) or np.isinf(y_max):
                print("Nieprawidłowe dane, ustawiam domyślny zakres osi Y.")
                self.ax1.set_ylim(-10000, 10000)
            else:
                data_range = y_max - y_min
                margin = (data_range / 2) if data_range != 0 else 1
                self.ax1.set_ylim(y_min - margin, y_max + margin)

            self.line1.set_data(np.arange(self.xlim), self.y)
            self.ax1.draw_artist(self.ax1.patch)
            self.ax1.draw_artist(self.line1)
            self.blit(self.ax1.bbox)

        except Exception as e:
            print(f"Błąd w update_plot: {e}")

    def start_data_loop(self):
        print("start_data_loop wywołane")
        self.running = True
        self.data_thread = threading.Thread(target=self.data_loop, daemon=True)
        self.data_thread.start()
        print("Wątek data_thread uruchomiony")

    def stop_data_loop(self):
        self.running = False
        if self.data_thread is not None and self.data_thread.is_alive():
            self.data_thread.join()
        self.safely_close_port()

    def restart_data_loop(self):
        self.stop_data_loop()
        time.sleep(0.2)
        self.start_data_loop()

    def safely_close_port(self):
        if hasattr(self, 'device') and self.device.serial.is_open:
            try:
                print("Zamykanie portu szeregowego przed ponownym otwarciem.")
                self.device.close()
            except Exception as e:
                print(f"Błąd zamykania portu: {e}")

    def filter_loop(self):
        while True:
            filter_task = self.filter_queue.get()
            if filter_task is None:
                continue

            filter_func, data, callback, args, kwargs = filter_task
            try:
                filtered_data = filter_func(data, *args, **kwargs)
                callback(filtered_data)
            except Exception as e:
                print(f"Błąd podczas filtrowania: {e}")

    def data_loop(self):
        try:
            self.device = DeviceManual(port="COM6", baudrate=115200)
            self.device.configure_binary_mode()

            print("Rozpoczęto odbieranie danych...")
            count = 0
            sample_interval = 5

            while self.running:
                data = self.device.serial.read(self.device.serial.in_waiting or 64)
                if data:
                    try:
                        packet = data.split(b'\xc0')[0]
                        if packet:
                            decoded_value = int.from_bytes(packet[-4:], 'little', signed=True)
                            print(f"Odebrana wartość: {decoded_value}")

                            count += 1
                            if count % sample_interval == 0:
                                filtered_value = [decoded_value]

                                if self.parent_window.lowpass_enabled:
                                    filtered_value = lowpass_filter_live(filtered_value, normal_cutoff=0.5)

                                if self.parent_window.highpass_enabled:
                                    filtered_value = highpass_filter_live(filtered_value, normal_cutoff=0.2)

                                if self.parent_window.notch_enabled:
                                    filtered_value = notch_filter(filtered_value, 50)

                                if self.parent_window.custom_enabled:
                                    try:
                                        custom_freq = int(self.parent_window.custom_filter_input.text())
                                        if 1 <= custom_freq <= 999:
                                            filtered_value = notch_filter(filtered_value, custom_freq,
                                                                          fs=self.sample_rate)
                                    except ValueError:
                                        print("Nieprawidłowa wartość dla filtru customowego.")

                                self.addedData.append(filtered_value[0])
                                count = 0

                    except Exception as e:
                        print(f"Błąd dekodowania: {e}")

        except Exception as e:
            print(f"Błąd komunikacji z urządzeniem: {e}")

        finally:
            if self.device:
                self.device.close()

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


def reset_com_port(devcon_path, device_id):
    try:
        print(f"Wyłączanie urządzenia {device_id}...")
        subprocess.run([devcon_path, "disable", device_id], check=True)
        time.sleep(1)
        print(f"Włączanie urządzenia {device_id}...")
        subprocess.run([devcon_path, "enable", device_id], check=True)
    except Exception as e:
        print(f"Błąd resetowania urządzenia: {e}")


def decode_tio_packet(protocol, packet):
    try:
        data = protocol.stream_data(packet, timeaxis=True)
        return data
    except Exception as e:
        print(f"Błąd dekodowania pakietu: {e}")
        return None

