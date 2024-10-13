import pandas as pd
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from backend import update_plot


def load_data(file_path):
    try:
        print(f"Loading data from {file_path}...")

        with open(file_path, 'r') as file:
            lines = file.readlines()

        if "Interval" in lines[0]:
            for i, line in enumerate(lines):
                if line.strip() == "":
                    data_start_line = i + 1
                    break
            else:
                data_start_line = 6

            data = pd.read_csv(file_path, sep="\t", skiprows=data_start_line, header=None, decimal=',')
            data.columns = ['time', 'gradient.B']

        elif not any(c.isalpha() for c in lines[0]):
            data = pd.read_csv(file_path, sep="\t", header=None, decimal=',')

            if len(data.columns) == 3:
                data.columns = ['unknown1', 'gradient.B', 'unknown2']
                data['time'] = data.index * 0.01
            else:
                raise ValueError("Niepoprawny format pliku bez nagłówków. Oczekiwano 3 kolumn.")
        else:
            data = pd.read_csv(file_path, sep="\t", decimal=',')
            if 'time' in data.columns and 'gradient.B' in data.columns:
                print("Załadowano dane z kolumny 'gradient.B'.")
            else:
                raise ValueError("Niepoprawny format pliku z nagłówkami.")

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
                window.original_data = data.copy()
                window.data = data
                update_plot(window, data)
                window.show_controls()
            else:
                QMessageBox.warning(window, "Warning", "Failed to load data from the file. Please check the file format.")
        except Exception as e:
            QMessageBox.critical(window, "Error", f"Error reading file: {e}")
            print(f"Error reading file: {e}")

