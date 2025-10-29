import pandas as pd
import numpy as np
from pathlib import Path
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from backend import update_plot, update_zoom, update_pan

def _infer_time_axis(raw_series):
    """
    Infer time axis in seconds and sampling rate from an integer ticker.
    Returns (time_seconds, sampling_rate_hz, scale_label).
    """
    diffs = raw_series.diff().dropna()
    diffs = diffs[diffs > 0]
    if diffs.empty:
        return raw_series.astype(float) * 0.0, None, "unknown"

    candidates = [
        ("seconds", 1.0),
        ("milliseconds", 1e-3),
        ("microseconds", 1e-6),
        ("nanoseconds", 1e-9),
    ]

    selected = None
    median_diff = float(np.median(diffs))
    for label, scale in candidates:
        dt = median_diff * scale
        if dt <= 0:
            continue
        fs = 1.0 / dt
        if 10.0 <= fs <= 5000.0:
            selected = (scale, fs, label)
            break

    if selected is None:
        scale, fs, label = 1.0, 1.0 / median_diff if median_diff else None, "fallback"
    else:
        scale, fs, label = selected

    offset = raw_series.iloc[0]
    time_axis = (raw_series - offset) * scale
    return time_axis, fs, label


def _infer_sampling_from_time(time_column):
    diffs = time_column.diff().dropna()
    diffs = diffs[diffs > 0]
    if diffs.empty:
        return None
    dt = float(np.median(diffs))
    if dt <= 0:
        return None
    return 1.0 / dt


def load_data(file_path):
    try:
        print(f"Loading data from {file_path}...")

        encoding = "Windows-1250"
        print(f"Using file encoding: {encoding}")

        with open(file_path, 'r', encoding=encoding) as file:
            lines = file.readlines()

        header_line = lines[0].strip()
        metadata = {
            "source": file_path,
            "encoding": encoding,
            "sampling_rate": None,
            "time_unit": None,
            "channels": [],
        }

        if "Timestamp" in header_line and "MKG Value" in header_line:
            data = pd.read_csv(file_path, header=0, sep=",", decimal='.', encoding=encoding)
            data.columns = [col.strip() for col in data.columns]

            if 'Timestamp' not in data.columns or 'MKG Value' not in data.columns:
                raise ValueError("File must contain 'Timestamp' and 'MKG Value' columns.")

            data['Timestamp'] = pd.to_datetime(data['Timestamp'], format="%H:%M:%S.%f")
            data['time'] = (data['Timestamp'] - data['Timestamp'].iloc[0]).dt.total_seconds()

            data = data.rename(columns={'MKG Value': 'gradient.B'})
            data['mkg'] = data['gradient.B']
            metadata["channels"] = ["mkg"]

        elif "Timestamp" in header_line and "EKG Value" in header_line:
            data = pd.read_csv(file_path, header=0, sep=",", decimal='.', encoding=encoding)
            data.columns = [col.strip() for col in data.columns]

            if 'Timestamp' not in data.columns or 'EKG Value' not in data.columns:
                raise ValueError("File must contain 'Timestamp' and 'EKG Value' columns.")

            data['Timestamp'] = pd.to_datetime(data['Timestamp'], format="%H:%M:%S.%f")
            data['time'] = (data['Timestamp'] - data['Timestamp'].iloc[0]).dt.total_seconds()

            data = data.rename(columns={'EKG Value': 'gradient.B'})
            data['mkg'] = data['gradient.B']
            metadata["channels"] = ["mkg"]

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
            data['mkg'] = data['gradient.B']
            metadata["channels"] = ["mkg"]

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
            data['mkg'] = data['gradient.B']
            metadata["channels"] = ["mkg"]

        elif not any(c.isalpha() for c in header_line):
            data = pd.read_csv(file_path, sep="\t", header=None, decimal=',', encoding=encoding)

            if len(data.columns) == 3:
                data.columns = ['raw_time', 'mkg', 'reference']
                time_axis, fs, unit_label = _infer_time_axis(data['raw_time'])
                data['time'] = time_axis
                metadata["sampling_rate"] = fs
                metadata["time_unit"] = unit_label
                metadata["channels"] = ['mkg', 'reference']
            else:
                raise ValueError("Incorrect file format without headers. 3 columns expected.")

        else:
            data = pd.read_csv(file_path, sep="\t", decimal=',', encoding=encoding)
            if 'time' in data.columns and 'gradient.B' in data.columns:
                print("Data from the 'gradient.B' column was loaded.")
                if 'mkg' not in data.columns:
                    data['mkg'] = data['gradient.B']
                metadata["channels"] = [col for col in data.columns if col not in ('time', 'Timestamp', 'Time')]
            else:
                raise ValueError("Incorrect header file format.")

        if 'time' not in data.columns and 'raw_time' in data.columns:
            time_axis, fs, unit_label = _infer_time_axis(data['raw_time'])
            data['time'] = time_axis
            metadata["sampling_rate"] = fs
            metadata["time_unit"] = unit_label

        data['time'] = pd.to_numeric(data['time'], errors='coerce')
        if 'gradient.B' not in data.columns and 'mkg' in data.columns:
            data['gradient.B'] = data['mkg']

        numeric_columns = [col for col in data.columns if col not in ('Timestamp', 'Time')]
        data[numeric_columns] = data[numeric_columns].apply(pd.to_numeric, errors='coerce')

        data = data.dropna(subset=['time'])
        if 'gradient.B' in data.columns:
            data = data.dropna(subset=['gradient.B'])

        if metadata["sampling_rate"] is None:
            metadata["sampling_rate"] = _infer_sampling_from_time(data['time'])

        if metadata["channels"]:
            metadata["channels"] = list(dict.fromkeys(metadata["channels"]))
        else:
            inferred_cols = [col for col in data.columns if col not in ('time', 'Timestamp', 'Time')]
            metadata["channels"] = inferred_cols

        data = data.reset_index(drop=True)
        data.attrs['sampling_rate'] = metadata["sampling_rate"]
        data.attrs['channels'] = metadata["channels"]
        data.attrs['time_unit'] = metadata.get("time_unit")

        print("Data loaded successfully.")
        return data, metadata

    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None


def aggregate_duplicate_timestamps(data, time_column='time', value_columns=None, method='mean'):
    if method == 'mean':
        agg_func = 'mean'
    elif method == 'median':
        agg_func = 'median'
    elif method == 'max':
        agg_func = 'max'
    elif method == 'min':
        agg_func = 'min'
    else:
        raise ValueError("Unknown aggregation method")

    if value_columns is None:
        value_columns = [col for col in data.columns if col != time_column]

    agg_map = {col: agg_func for col in value_columns}
    data_agg = data.groupby(time_column, as_index=False).agg(agg_map)
    return data_agg


def _find_related_overlay_path(file_path):
    path = Path(file_path)
    stem = path.stem
    suffix = path.suffix
    candidates = []

    if stem.lower().endswith('_ard'):
        base_stem = stem[:-4]
        if base_stem:
            candidates.append(path.with_name(base_stem + suffix))
    else:
        candidates.append(path.with_name(stem + '_ard' + suffix))
        candidates.append(path.with_name(stem + '_ARD' + suffix))

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


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

            data, metadata = load_data(file_path)
            if data is not None:
                window.reset_controls_to_default()
                value_columns = [col for col in data.columns if col != 'time']
                data = aggregate_duplicate_timestamps(data, time_column='time', value_columns=value_columns, method='mean')

                derived_channels = metadata.get("channels") or [
                    col for col in data.columns if col not in ('time', 'raw_time', 'Timestamp', 'Time')
                ]
                if 'gradient.B' in data.columns and 'gradient.B' not in derived_channels:
                    derived_channels.append('gradient.B')

                sampling_rate = metadata.get("sampling_rate", data.attrs.get('sampling_rate'))
                data.attrs['sampling_rate'] = sampling_rate
                data.attrs['channels'] = list(dict.fromkeys(derived_channels))
                if metadata.get("time_unit"):
                    data.attrs['time_unit'] = metadata.get("time_unit")

                window.original_data = data.copy()
                window.data = data.copy()

                window.sampling_rate = sampling_rate
                window.ecg_overlay_data = None
                window.ecg_overlay_column = None
                window.ecg_overlay_sampling_rate = None
                window.ecg_overlay_path = None
                if hasattr(window, 'ecg_overlay_checkbox'):
                    window.ecg_overlay_checkbox.setChecked(False)
                    window.ecg_overlay_checkbox.setEnabled(False)
                    window.ecg_overlay_checkbox.setVisible(False)

                overlay_candidate = _find_related_overlay_path(file_path)
                if overlay_candidate:
                    overlay_data, overlay_meta = load_data(str(overlay_candidate))
                    if overlay_data is not None:
                        overlay_value_columns = [col for col in overlay_data.columns if col != 'time']
                        overlay_data = aggregate_duplicate_timestamps(overlay_data, time_column='time', value_columns=overlay_value_columns, method='mean')
                        overlay_column = None
                        for candidate_col in ('reference', 'ecg', 'ECG Value', 'gradient.B', 'mkg'):
                            if candidate_col in overlay_data.columns:
                                overlay_column = candidate_col
                                break
                        if overlay_column:
                            window.ecg_overlay_data = overlay_data
                            window.ecg_overlay_column = overlay_column
                            window.ecg_overlay_sampling_rate = overlay_meta.get('sampling_rate', overlay_data.attrs.get('sampling_rate'))
                            window.ecg_overlay_baseline_sec = 0.6
                            window.ecg_overlay_baseline_poly = 3
                            window.ecg_overlay_savgol_poly = 3
                            window.ecg_overlay_savgol_sec = 0.018
                            window.ecg_overlay_path = str(overlay_candidate)
                            if hasattr(window, 'ecg_overlay_checkbox'):
                                window.ecg_overlay_checkbox.setText(f"ECG overlay ({overlay_candidate.name})")
                                window.ecg_overlay_checkbox.setVisible(True)
                                window.ecg_overlay_checkbox.setEnabled(True)
                                window.ecg_overlay_checkbox.setChecked(False)
                        else:
                            window.ecg_overlay_data = None
                            window.ecg_overlay_column = None
                            window.ecg_overlay_sampling_rate = None
                            window.ecg_overlay_path = None
                window.last_sampling_rate = sampling_rate
                window.available_channels = data.attrs.get('channels', [])

                preferred_primary = window.primary_channel if window.primary_channel in window.available_channels else None
                if not preferred_primary:
                    for candidate in ('mkg', 'gradient.B'):
                        if candidate in window.available_channels:
                            preferred_primary = candidate
                            break
                if not preferred_primary and window.available_channels:
                    preferred_primary = window.available_channels[0]
                window.primary_channel = preferred_primary

                if window.primary_channel:
                    potential_refs = [ch for ch in window.available_channels if ch not in (window.primary_channel, 'gradient.B')]
                    if not potential_refs:
                        potential_refs = [ch for ch in window.available_channels if ch != window.primary_channel]
                    window.reference_channel = potential_refs[0] if potential_refs else None
                else:
                    window.reference_channel = None

                if hasattr(window, 'configure_channel_selectors'):
                    window.configure_channel_selectors(window.available_channels)

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

