import pandas as pd
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from backend import update_plot


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
                window.data = data
                update_plot(window, data)
                window.show_time_range_controls()
            else:
                QMessageBox.warning(window, "Warning", "Failed to load data from the file. Please check the file format.")
        except Exception as e:
            QMessageBox.critical(window, "Error", f"Error reading file: {e}")
            print(f"Error reading file: {e}")
