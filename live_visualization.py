from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QFileDialog, QPushButton, QHBoxLayout, QCheckBox, QLabel, QSizePolicy, QFrame
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
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
from tio_protocol import TIOProtocol, TL_PTYPE_STREAM0
import slip
from slip import decode
from queue import Queue
from initialization import DeviceManual


class RealTimePlotWindow(QMainWindow):
    closed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Data Plot")
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
        self.toggle_theme.setStyleSheet("""
            QCheckBox::indicator {
                width: 40px;
                height: 20px;
                border-radius: 10px;
                background-color: #ccc;
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

        self.theme_label = QLabel("Tryb ciemny")
        self.theme_label.setStyleSheet("font-size: 14px; padding: 0px;")

        self.top_layout.addWidget(self.toggle_theme, alignment=Qt.AlignTop | Qt.AlignRight)
        self.top_layout.addWidget(self.theme_label, alignment=Qt.AlignTop | Qt.AlignRight)

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

        self.canvas.start_data_loop()
        self.change_theme(0)

    def change_theme(self, state):
        if state == 2:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2c2c2c;
                }
                QLabel, QCheckBox, QPushButton {
                    color: #f0f0f0;
                }
                QPushButton {
                    background-color: #555;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #333;
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
                }
                QPushButton {
                    background-color: #2d89ef;
                    color: white;
                    border-radius: 10px;
                }
                QPushButton:hover {
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
        self.serial_port = None
        self.thread = None
        self.setAttribute(Qt.WA_DeleteOnClose, True)

    def on_destroyed(self):
        print("RealTimePlotWindow zostało zniszczone.")

    def add_data(self, value):
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
                self.ax1.set_ylim(y_min - 10, y_max + 10)

            self.line1.set_data(np.arange(self.xlim), self.y)
            self.ax1.draw_artist(self.ax1.patch)
            self.ax1.draw_artist(self.line1)
            self.blit(self.ax1.bbox)

        except Exception as e:
            print(f"Błąd w update_plot: {e}")

    def start_data_loop(self):
        self.running = True
        self.thread = threading.Thread(target=self.data_loop, daemon=True)
        self.thread.start()

    def stop_data_loop(self):
        self.running = False
        if self.thread is not None and self.thread.is_alive():
            self.thread.join()
        if self.serial_port is not None:
            try:
                if self.serial_port.is_open:
                    self.serial_port.close()
            except Exception as e:
                print(f"Error closing serial port: {e}")

    def restart_data_loop(self):
        self.stop_data_loop()
        time.sleep(0.2)
        self.start_data_loop()

    def safely_close_port(self):
        if self.serial_port and self.serial_port.is_open:
            try:
                print("Zamykanie portu szeregowego przed ponownym otwarciem.")
                self.serial_port.close()
            except Exception as e:
                print(f"Błąd zamykania portu: {e}")

    def data_loop(self):
        try:
            self.device = DeviceManual(port="COM6", baudrate=115200)
            self.device.configure_binary_mode()

            print("Rozpoczęto odbieranie danych...")
            while self.running:
                data = self.device.serial.read(self.device.serial.in_waiting or 64)
                if data:
                    try:
                        packet = data.split(b'\xc0')[0]
                        if packet:
                            decoded_value = int.from_bytes(packet[-4:], 'little', signed=True)
                            print(f"Odebrana wartość: {decoded_value}")
                            self.addedData.append(decoded_value)
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

