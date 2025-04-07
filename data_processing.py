import pandas as pd
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from backend import update_plot, update_zoom, update_pan


def load_data(file_path):
    try:
        print(f"Loading data from {file_path}...")

        encoding = "Windows-1250"
        print(f"Using file encoding: {encoding}")

        with open(file_path, 'r', encoding=encoding) as file:
            lines = file.readlines()

        header_line = lines[0].strip()

        if "Timestamp" in header_line and "MKG Value" in header_line:
            data = pd.read_csv(file_path, header=0, sep=",", decimal='.', encoding=encoding)
            data.columns = [col.strip() for col in data.columns]

            if 'Timestamp' not in data.columns or 'MKG Value' not in data.columns:
                raise ValueError("File must contain 'Timestamp' and 'MKG Value' columns.")

            data['Timestamp'] = pd.to_datetime(data['Timestamp'], format="%H:%M:%S.%f")
            data['time'] = (data['Timestamp'] - data['Timestamp'].iloc[0]).dt.total_seconds()

            data = data.rename(columns={'MKG Value': 'gradient.B'})
            data = data[['time', 'gradient.B']]

        elif "Time" in header_line and "Value" in header_line:
            data = pd.read_csv(file_path, header=0, sep=",", decimal='.', encoding=encoding)

            data.columns = [col.strip().capitalize() for col in data.columns]

            expected_columns = ['Time', 'Value']
            if list(data.columns) != expected_columns:
                raise ValueError(
                    f"Incorrect file format. Headers expected:  {expected_columns}, found: {list(data.columns)}.")

            data['Time'] = pd.to_datetime(data['Time'], format="%H:%M:%S.%f")
            data['time'] = (data['Time'] - data['Time'].iloc[0]).dt.total_seconds()

            data = data.rename(columns={'Value': 'gradient.B'})

            data = data[['time', 'gradient.B']]

        elif "Interval" in header_line:
            for i, line in enumerate(lines):
                if line.strip() == "":
                    data_start_line = i + 1
                    break
            else:
                data_start_line = 6

            data = pd.read_csv(file_path, sep="\t", skiprows=data_start_line, header=None, decimal=',',
                               encoding=encoding)
            data.columns = ['time', 'gradient.B']

        elif not any(c.isalpha() for c in header_line):
            data = pd.read_csv(file_path, sep="\t", header=None, decimal=',', encoding=encoding)

            if len(data.columns) == 3:
                data.columns = ['unknown1', 'gradient.B', 'unknown2']
                data['time'] = data.index * 0.01
            else:
                raise ValueError("Incorrect file format without headers. 3 columns expected.")

        else:
            data = pd.read_csv(file_path, sep="\t", decimal=',', encoding=encoding)
            if 'time' in data.columns and 'gradient.B' in data.columns:
                print("Data from the ‘gradient.B’ column was loaded.")
            else:
                raise ValueError("Incorrect header file format.")

        data['time'] = pd.to_numeric(data['time'], errors='coerce')
        data['gradient.B'] = pd.to_numeric(data['gradient.B'], errors='coerce')
        data = data.dropna(subset=['time', 'gradient.B'])
        print("Data loaded successfully.")
        return data

    except Exception as e:
        print(f"Error loading data: {e}")
        return None


def adjust_duplicate_timestamps(data, time_column='time', time_step=0.001):
    data = data.sort_values(by=[time_column]).reset_index(drop=True)
    seen_timestamps = set()

    for idx in range(len(data)):
        original_time = data.loc[idx, time_column]
        while original_time in seen_timestamps:
            original_time += time_step
        seen_timestamps.add(original_time)
        data.loc[idx, time_column] = original_time

    print("Adjusted timestamps (first 10 rows):")
    print(data[[time_column]].head(10))

    return data


def load_and_plot_file(window):
    options = QFileDialog.Options()
    file_path, _ = QFileDialog.getOpenFileName(window, "Select File", "", "All Files (*);;Text Files (*.txt);;TSV Files (*.tsv)", options=options)
    if file_path:
        window.file_path_label.setText(f"Selected file: {file_path}")
        try:
            update_zoom(window, 1)
            window.zoom_slider.setValue(1)
            update_pan(window, 50)
            window.pan_slider.setValue(50)

            data = load_data(file_path)
            window.reset_controls_to_default()
            if data is not None:
                data = adjust_duplicate_timestamps(data, time_column='time', time_step=0.001)

                window.original_data = data.copy()
                window.data = data

                window.current_time_from = None
                window.current_time_to = None

                update_plot(window, data)

                update_zoom(window, 1)
                update_pan(window, 50)
                window.show_controls()
            else:
                QMessageBox.warning(window, "Warning", "Failed to load data from the file. Please check the file format.")
            window.pan_slider.setEnabled(False)
        except Exception as e:
            QMessageBox.critical(window, "Error", f"Error reading file: {e}")
            print(f"Error reading file: {e}")
