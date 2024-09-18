import pandas as pd
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout, QFrame
from canvas import MplCanvas


def load_data(file_path):
    try:
        print(f"Loading data from {file_path}...")
        data = pd.read_csv(file_path, sep="\t", on_bad_lines='skip', decimal=',')
        data['time'] = pd.to_numeric(data['time'], errors='coerce')
        data['gradient.B'] = pd.to_numeric(data['gradient.B'], errors='coerce')
        data = data.dropna(subset=['time', 'gradient.B'])
        print("Data loaded successfully.")
        return data
    except Exception as e:
        print(f"Error loading data: {e}")
        return None


def load_and_plot_file(window):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getOpenFileName(window, "Select File", "", "All Files (*);;Text Files (*.txt);;TSV Files (*.tsv)", options=options)
    if file_path:
        window.file_path_label.setText(f"Selected file: {file_path}")
        try:
            data = load_data(file_path)
            if data is not None:
                window.current_data = data
                update_plot(window, data)
            else:
                QMessageBox.warning(window, "Warning", "Failed to load data from the file. Please check the file format.")
        except Exception as e:
            QMessageBox.critical(window, "Error", f"Error reading file: {e}")
            print(f"Error reading file: {e}")


def update_plot(window, data):
    if data is not None:
        if window.canvas_frame is None:
            print("Tworzenie nowego kontenera dla płótna...")
            window.canvas_frame = QFrame(window)

            if window.toggle_theme.isChecked():
                window.canvas_frame.setStyleSheet("""
                    QFrame {
                        border: 1px solid #888888;
                        border-radius: 15px;
                        background-color: #2c2c2c;
                    }
                """)
            else:
                window.canvas_frame.setStyleSheet("""
                    QFrame {
                        border: 1px solid #2d89ef;
                        border-radius: 15px;
                        background-color: white;
                    }
                """)

            window.layout.addWidget(window.canvas_frame)
            print("Kontener został dodany do layoutu.")

            window.canvas = MplCanvas(window.canvas_frame, width=8, height=6, dpi=100)
            layout_canvas = QVBoxLayout()
            layout_canvas.addWidget(window.canvas)
            window.canvas_frame.setLayout(layout_canvas)
            print("Płótno wykresu zostało stworzone i dodane do kontenera.")

        window.canvas.figure.clf()
        window.canvas.axes = window.canvas.figure.add_subplot(111)

        if window.toggle_theme.isChecked():
            window.canvas.axes.set_facecolor('#2c2c2c')
            window.canvas.figure.patch.set_facecolor('#2c2c2c')
            window.canvas.axes.spines['bottom'].set_color('white')
            window.canvas.axes.spines['left'].set_color('white')
            window.canvas.axes.tick_params(axis='x', colors='white')
            window.canvas.axes.tick_params(axis='y', colors='white')
            window.canvas.axes.xaxis.label.set_color('white')
            window.canvas.axes.yaxis.label.set_color('white')
            window.canvas.axes.title.set_color('white')
            line_color = 'cyan'
        else:
            window.canvas.axes.set_facecolor('white')
            window.canvas.figure.patch.set_facecolor('white')
            window.canvas.axes.spines['bottom'].set_color('black')
            window.canvas.axes.spines['left'].set_color('black')
            window.canvas.axes.tick_params(axis='x', colors='black')
            window.canvas.axes.tick_params(axis='y', colors='black')
            window.canvas.axes.xaxis.label.set_color('black')
            window.canvas.axes.yaxis.label.set_color('black')
            window.canvas.axes.title.set_color('black')
            line_color = 'blue'

        window.canvas.axes.plot(data['time'], data['gradient.B'], label='Gradient B', color=line_color)
        window.canvas.axes.set_xlabel('Time')
        window.canvas.axes.set_ylabel('Magnetic Field (B)')
        window.canvas.axes.set_title('Magnetocardiogram Visualization')
        window.canvas.axes.legend()

        window.canvas.draw()
        print("Plot updated successfully.")
        window.setFixedSize(1200, 700)
