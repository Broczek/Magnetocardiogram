import json
import os
import sys
import time
from typing import Dict, List, Optional

import numpy as np
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QVBoxLayout, QFrame, QFileDialog, QApplication
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import serial.tools.list_ports

from signal_processing import (
    DEFAULT_FS,
    FilterSettings,
    apply_filter_pipeline,
    detect_r_peaks,
    extract_rr_features,
    refine_line_frequency,
)

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

IMAGES_DIR = os.path.join(BASE_DIR, "images")

DOT_BLACK_PATH = os.path.join(IMAGES_DIR, "dot_black.png").replace("\\", "/")
DOT_WHITE_PATH = os.path.join(IMAGES_DIR, "dot_white.png").replace("\\", "/")


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setStyleSheet("background-color: transparent;")


def detect_sensor_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == 0x0483 and port.pid == 0x5740:
            return port.device
    return None


def state_change(window):
    if window.isActiveWindow():
        window.setWindowIcon(QIcon(os.path.join(IMAGES_DIR, "Icon.png")))
    else:
        window.setWindowIcon(QIcon(os.path.join(IMAGES_DIR, "Icon_black.png")))


def show_controls(window):
    window.time_range_label.show()
    window.time_from_input.show()
    window.time_to_input.show()
    window.set_time_button.show()
    window.zoom_label.show()
    window.zoom_slider.show()
    window.pan_label.show()
    window.pan_slider.show()
    window.filters_label.show()
    if hasattr(window, 'channel_label'):
        window.channel_label.show()
    if hasattr(window, 'channel_selector'):
        window.channel_selector.show()
    if hasattr(window, 'processing_profile_label'):
        window.processing_profile_label.show()
    if hasattr(window, 'processing_profile_selector'):
        window.processing_profile_selector.show()
    if hasattr(window, 'reference_label'):
        window.reference_label.show()
    if hasattr(window, 'reference_selector'):
        window.reference_selector.show()
    window.lowpass_filter.show()
    window.highpass_filter.show()
    window.filter_50hz.show()
    window.filter_100hz.show()
    window.filter_150hz.show()
    if hasattr(window, 'reference_cancel_checkbox'):
        window.reference_cancel_checkbox.show()
    if hasattr(window, 'auto_notch_checkbox'):
        window.auto_notch_checkbox.show()
    if hasattr(window, 'baseline_remove_checkbox'):
        window.baseline_remove_checkbox.show()
    if hasattr(window, 'savgol_smooth_checkbox'):
        window.savgol_smooth_checkbox.show()
    if hasattr(window, 'despike_filter'):
        window.despike_filter.show()
    if hasattr(window, 'feature_toggle'):
        window.feature_toggle.show()
    if hasattr(window, 'ecg_overlay_checkbox'):
        window.ecg_overlay_checkbox.setVisible(getattr(window, 'ecg_overlay_data', None) is not None)
    window.custom_filter_1_input.show()
    window.custom_filter_1_apply.show()
    window.custom_filter_2_input.show()
    window.custom_filter_2_apply.show()
    window.file_name_input.show()
    window.save_txt.show()
    window.save_tsv.show()
    window.save_xlsx.show()
    window.save_button.show()
    window.setFixedSize(1200, 950)


def validate_custom_filter(input_field, apply_checkbox):
    text = input_field.text()
    if text.isdigit() and 1 <= int(text) <= 230:
        apply_checkbox.setEnabled(True)
    else:
        apply_checkbox.setEnabled(False)


def validate_input(window, input_field, field_type):
    try:
        value = float(input_field.text())
        min_time = window.data['time'].min()
        max_time = window.data['time'].max()

        if field_type == "from":
            if value < min_time:
                window.error_from_label.setText(f"Min value is {min_time:.2f} seconds.")
                input_field.setStyleSheet("border: 2px solid red; border-radius: 10px;")
                window.error_from_label.show()
            else:
                window.error_from_label.hide()
                input_field.setStyleSheet("border: 1px solid #ccc; border-radius: 10px;")
        elif field_type == "to":
            if value > max_time:
                window.error_to_label.setText(f"Max value is {max_time:.2f} seconds.")
                input_field.setStyleSheet("border: 2px solid red; border-radius: 10px;")
                window.error_to_label.show()
            else:
                window.error_to_label.hide()
                input_field.setStyleSheet("border: 1px solid #ccc; border-radius: 10px;")
    except ValueError:
        if field_type == "from":
            window.error_from_label.setText("Invalid input format.")
            input_field.setStyleSheet("border: 2px solid red; border-radius: 10px;")
            window.error_from_label.show()
        elif field_type == "to":
            window.error_to_label.setText("Invalid input format.")
            input_field.setStyleSheet("border: 2px solid red; border-radius: 10px;")
            window.error_to_label.show()


def apply_time_range(window):
    validate_input(window, window.time_from_input, "from")
    validate_input(window, window.time_to_input, "to")

    if not window.error_from_label.isVisible() and not window.error_to_label.isVisible():
        try:
            time_from = float(window.time_from_input.text())
            time_to = float(window.time_to_input.text())

            if time_from >= time_to:
                window.error_from_label.setText("'From' must be less than 'To'.")
                window.time_from_input.setStyleSheet("border: 2px solid red; border-radius: 10px;")
                window.error_from_label.show()
                return

            filtered_data = window.data[(window.data['time'] >= time_from) & (window.data['time'] <= time_to)]

            window.current_time_from = time_from
            window.current_time_to = time_to

            update_plot(window, filtered_data, time_from, time_to)

        except ValueError:
            pass


def get_sampling_rate(window) -> float:
    for attr_name in ('sampling_rate',):
        sr = getattr(window, attr_name, None)
        if sr and sr > 0:
            return sr

    for dataset in (getattr(window, 'data', None), getattr(window, 'original_data', None)):
        if dataset is not None:
            sr = dataset.attrs.get('sampling_rate')
            if sr and sr > 0:
                return sr

    return DEFAULT_FS


def get_primary_channel(window, data) -> Optional[str]:
    preferred = getattr(window, 'primary_channel', None)
    if preferred and preferred in data.columns:
        return preferred
    if 'gradient.B' in data.columns:
        return 'gradient.B'
    numeric_columns = [col for col in data.columns if col != 'time']
    return numeric_columns[0] if numeric_columns else None


def get_reference_series(window, data):
    checkbox = getattr(window, 'reference_cancel_checkbox', None)
    if checkbox is None or not checkbox.isChecked():
        return None
    reference_column = getattr(window, 'reference_channel', None)
    if reference_column and reference_column in data.columns:
        return data[reference_column].to_numpy(dtype=float)
    return None


def collect_notch_frequencies(window, fs: float) -> (List[float], List[float]):
    builtin = []
    for freq, checkbox in ((50.0, window.filter_50hz),
                           (100.0, window.filter_100hz),
                           (150.0, window.filter_150hz)):
        if checkbox.isChecked():
            builtin.append(freq)

    ceiling = max(1.0, 0.45 * fs)
    custom: List[float] = []
    custom_inputs = (
        (getattr(window, 'custom_filter_1_input', None), getattr(window, 'custom_filter_1_apply', None)),
        (getattr(window, 'custom_filter_2_input', None), getattr(window, 'custom_filter_2_apply', None)),
    )
    for input_field, checkbox in custom_inputs:
        if input_field is None or checkbox is None or not checkbox.isChecked():
            continue
        try:
            freq = float(input_field.text())
        except (TypeError, ValueError):
            continue
        if 1.0 <= freq <= ceiling:
            custom.append(freq)
    return builtin, custom


def apply_filters(window, data):
    if data is None or data.empty:
        return data

    fs = get_sampling_rate(window)
    primary_column = get_primary_channel(window, data)
    if primary_column is None:
        return data

    signal = data[primary_column].to_numpy(dtype=float)
    reference_signal = get_reference_series(window, data)
    builtin_notches, custom_notches = collect_notch_frequencies(window, fs)
    refined_builtin = []
    for freq in builtin_notches:
        refined = refine_line_frequency(signal, fs, freq, window_hz=1.2)
        if refined not in refined_builtin:
            refined_builtin.append(refined)
    builtin_notches = refined_builtin

    refined_custom = []
    for freq in custom_notches:
        refined = refine_line_frequency(signal, fs, freq, window_hz=1.2)
        if refined not in refined_custom:
            refined_custom.append(refined)
    custom_notches = refined_custom
    baseline_checkbox = getattr(window, 'baseline_remove_checkbox', None)
    savgol_checkbox = getattr(window, 'savgol_smooth_checkbox', None)
    baseline_enabled = baseline_checkbox.isChecked() if baseline_checkbox else False
    savgol_enabled = savgol_checkbox.isChecked() if savgol_checkbox else False
    auto_notch_checkbox = getattr(window, 'auto_notch_checkbox', None)
    auto_notch_enabled = auto_notch_checkbox.isChecked() if auto_notch_checkbox else True

    custom_notches = refined_custom

    low_default = getattr(window, 'highpass_cutoff', 0.5)
    high_default = getattr(window, 'lowpass_cutoff', min(150.0, 0.45 * fs))

    bandpass_low, bandpass_high = getattr(window.bandpass_slider, 'value', lambda: (low_default, high_default))()
    bandpass_low = max(0.1, float(bandpass_low))
    bandpass_high = min(float(bandpass_high), fs * 0.49)
    if bandpass_high <= bandpass_low:
        bandpass_high = min(fs * 0.49, bandpass_low + 5.0)

    settings = FilterSettings(
        fs=fs,
        use_highpass=window.highpass_filter.isChecked(),
        highpass_cutoff=low_default,
        use_lowpass=window.lowpass_filter.isChecked(),
        lowpass_cutoff=high_default,
        use_bandpass=window.bandpass_apply.isChecked(),
        bandpass_range=(bandpass_low, bandpass_high),
        notch_freqs=tuple(builtin_notches),
        custom_notch_freqs=tuple(custom_notches),
        reference_signal=reference_signal,
        use_reference_cancel=reference_signal is not None,
        use_baseline=baseline_enabled,
        baseline_window_sec=getattr(window, 'baseline_window_sec', 0.7),
        baseline_polyorder=getattr(window, 'baseline_polyorder', 3),
        use_savgol_smooth=savgol_enabled,
        savgol_window_sec=getattr(window, 'savgol_window_sec', 0.025),
        savgol_polyorder=getattr(window, 'savgol_polyorder', 3),
        auto_notch=auto_notch_enabled,
        apply_hampel=getattr(window, 'despike_filter', None) is not None and window.despike_filter.isChecked(),
        hampel_window=getattr(window, 'hampel_window', 11),
        hampel_sigmas=getattr(window, 'hampel_sigmas', 3.0),
    )

    filtered_signal, debug_info = apply_filter_pipeline(signal, settings)
    filtered = data.copy()
    filtered['gradient.B'] = filtered_signal
    filtered.attrs['filter_debug'] = debug_info

    peaks_array = np.array([], dtype=int)
    feature_summary: Dict[str, float] = {}
    feature_toggle = getattr(window, 'feature_toggle', None)
    if feature_toggle is not None and feature_toggle.isChecked():
        std_estimate = float(np.std(filtered_signal)) if filtered_signal.size else 0.0
        prominence = getattr(window, 'peak_prominence', None)
        if prominence is None:
            prominence = max(0.05, 0.35 * std_estimate)
        peaks_array, peak_props = detect_r_peaks(filtered_signal, fs, prominence=prominence)
        feature_summary = extract_rr_features(filtered['time'].to_numpy(), peaks_array, fs)
        filtered.attrs['peak_props'] = peak_props

    filtered.attrs['peaks'] = peaks_array
    filtered.attrs['features'] = feature_summary

    window.last_filter_debug = debug_info
    window.last_sampling_rate = fs
    window.last_primary_channel = primary_column
    window.last_detected_peaks = peaks_array
    window.last_feature_summary = feature_summary

    return filtered




def compute_ecg_overlay_series(window, filtered_data):
    window.last_overlay_debug = {}
    checkbox = getattr(window, 'ecg_overlay_checkbox', None)
    if checkbox is None or not checkbox.isChecked():
        return None

    overlay_df = getattr(window, 'ecg_overlay_data', None)
    overlay_column = getattr(window, 'ecg_overlay_column', None)
    if overlay_df is None or overlay_df.empty or not overlay_column or overlay_column not in overlay_df.columns:
        return None

    times = overlay_df['time'].to_numpy(dtype=float)
    values = overlay_df[overlay_column].to_numpy(dtype=float)
    if times.size < 2 or values.size == 0:
        return None

    overlay_fs = getattr(window, 'ecg_overlay_sampling_rate', None) or get_sampling_rate(window)
    builtin_notches, custom_notches = collect_notch_frequencies(window, overlay_fs)

    refined_builtin = []
    for freq in builtin_notches:
        refined = refine_line_frequency(values, overlay_fs, freq, window_hz=1.2)
        if refined not in refined_builtin:
            refined_builtin.append(refined)
    builtin_notches = refined_builtin

    refined_custom = []
    for freq in custom_notches:
        refined = refine_line_frequency(values, overlay_fs, freq, window_hz=1.2)
        if refined not in refined_custom:
            refined_custom.append(refined)
    custom_notches = refined_custom

    auto_notch_checkbox = getattr(window, 'auto_notch_checkbox', None)
    auto_notch_enabled = auto_notch_checkbox.isChecked() if auto_notch_checkbox else True

    settings = FilterSettings(
        fs=overlay_fs,
        use_bandpass=True,
        bandpass_range=(5.0, min(45.0, 0.45 * overlay_fs)),
        use_baseline=True,
        baseline_window_sec=getattr(window, 'ecg_overlay_baseline_sec', 0.6),
        baseline_polyorder=getattr(window, 'ecg_overlay_baseline_poly', 3),
        use_savgol_smooth=True,
        savgol_window_sec=getattr(window, 'ecg_overlay_savgol_sec', 0.018),
        savgol_polyorder=getattr(window, 'ecg_overlay_savgol_poly', 3),
        notch_freqs=tuple(builtin_notches),
        custom_notch_freqs=tuple(custom_notches),
        auto_notch=auto_notch_enabled,
    )

    filtered_overlay, overlay_debug = apply_filter_pipeline(values, settings)
    window.last_overlay_debug = overlay_debug

    target_times = filtered_data['time'].to_numpy(dtype=float)
    if target_times.size == 0:
        return None

    overlay_interp = np.interp(target_times, times, filtered_overlay, left=np.nan, right=np.nan)
    mask = np.isfinite(overlay_interp)
    if not np.any(mask):
        return None

    overlay_interp = np.nan_to_num(overlay_interp, nan=0.0)
    overlay_interp -= np.median(overlay_interp)
    max_abs = np.max(np.abs(overlay_interp))
    if max_abs > 0:
        overlay_interp /= max_abs

    range_mkg = filtered_data['gradient.B'].max() - filtered_data['gradient.B'].min()
    scale = range_mkg * 0.4 if range_mkg > 0 else 1.0
    overlay_interp *= scale
    offset = (filtered_data['gradient.B'].max() + filtered_data['gradient.B'].min()) / 2.0
    overlay_interp += offset

    return overlay_interp


def refresh_plot(window):
    zoom_value = None
    pan_value = None
    zoom_enabled = False
    pan_enabled = False

    if hasattr(window, 'zoom_slider'):
        try:
            zoom_value = window.zoom_slider.value()
            zoom_enabled = window.zoom_slider.isEnabled()
        except Exception:
            zoom_value = None
            zoom_enabled = False

    if hasattr(window, 'pan_slider'):
        try:
            pan_value = window.pan_slider.value()
            pan_enabled = window.pan_slider.isEnabled()
        except Exception:
            pan_value = None
            pan_enabled = False

    if window.current_time_from is not None and window.current_time_to is not None:
        subset = window.data[(window.data['time'] >= window.current_time_from) &
                             (window.data['time'] <= window.current_time_to)]
        update_plot(window, subset, window.current_time_from, window.current_time_to)
    else:
        update_plot(window, window.data)

    if zoom_value is not None:
        try:
            previous_state = window.zoom_slider.blockSignals(True)
            window.zoom_slider.setValue(zoom_value)
        finally:
            window.zoom_slider.blockSignals(previous_state)
        if zoom_enabled:
            update_zoom(window, zoom_value)

    if pan_value is not None:
        try:
            previous_state = window.pan_slider.blockSignals(True)
            window.pan_slider.setValue(pan_value)
        finally:
            window.pan_slider.blockSignals(previous_state)
        if pan_enabled and window.pan_slider.isEnabled():
            update_pan(window, pan_value)


def handle_bandpass_apply_toggle(window):
    refresh_plot(window)


def update_slider_labels(window):
    low_value, high_value = window.bandpass_slider.value()
    try:
        window.bandpass_slider._min_label.setValue(low_value)
        window.bandpass_slider._max_label.setValue(max(high_value, low_value + 5))
    except AttributeError as e:
        print(f"Label update error: {e}")

    if window.bandpass_apply.isChecked():
        refresh_plot(window)


def validate_bandpass_values(window):
    low_value, high_value = window.bandpass_slider.value()
    fs = get_sampling_rate(window)

    min_gap = 5.0
    adjusted_low = max(0.1, float(low_value))
    adjusted_high = float(high_value)

    changed = False
    if adjusted_high <= adjusted_low + min_gap:
        adjusted_high = adjusted_low + min_gap
        changed = True

    if fs and fs > 0:
        max_high = fs * 0.49
        if adjusted_high > max_high:
            adjusted_high = max_high
            changed = True

    if changed:
        previous_state = window.bandpass_slider.blockSignals(True)
        try:
            window.bandpass_slider.setValue((adjusted_low, adjusted_high))
        finally:
            window.bandpass_slider.blockSignals(previous_state)

    update_slider_labels(window)
    QApplication.processEvents()


def handle_filter_toggle(window, filter_name):
    refresh_plot(window)


def save_data(window):
    file_name = window.file_name_input.text()
    if not file_name:
        print("The file name cannot be empty!")
        return

    formats = []
    if window.save_txt.isChecked():
        formats.append("txt")
    if window.save_tsv.isChecked():
        formats.append("tsv")
    if window.save_xlsx.isChecked():
        formats.append("xlsx")

    if not formats:
        print("Select at least one recording format.")
        return

    directory = QFileDialog.getExistingDirectory(window, "Select Directory")
    if not directory:
        return

    save_folder = os.path.join(directory, file_name)
    os.makedirs(save_folder, exist_ok=True)

    if window.data is None or not hasattr(window, 'original_data'):
        print("No data to be saved.")
        return

    filtered_data = apply_filters(window, window.original_data.copy())

    if window.current_time_from is not None and window.current_time_to is not None:
        filtered_data = filtered_data[(filtered_data['time'] >= window.current_time_from) &
                                      (filtered_data['time'] <= window.current_time_to)]

    feature_summary = filtered_data.attrs.get('features', {})
    filter_debug = filtered_data.attrs.get('filter_debug', {})
    if feature_summary:
        features_path = os.path.join(save_folder, f"{file_name}_features.json")
        export_payload = {
            "features": feature_summary,
            "sampling_rate": get_sampling_rate(window),
            "filters": filter_debug,
        }
        with open(features_path, "w", encoding="utf-8") as feature_file:
            json.dump(export_payload, feature_file, indent=2)
        print(f"Saved feature summary to {features_path}")

    if "txt" in formats:
        txt_file_path = os.path.join(save_folder, f"{file_name}.txt")
        filtered_data.to_csv(txt_file_path, sep='\t', index=False)
        print(f"Saved filtered data to {txt_file_path}")

    if "tsv" in formats:
        tsv_file_path = os.path.join(save_folder, f"{file_name}.tsv")
        filtered_data.to_csv(tsv_file_path, sep='\t', index=False)
        print(f"Saved filtered data to {tsv_file_path}")

    if "xlsx" in formats:
        xlsx_file_path = os.path.join(save_folder, f"{file_name}.xlsx")
        filtered_data.to_excel(xlsx_file_path, index=False)
        print(f"Saved filtered data to {xlsx_file_path}")


def update_plot(window, data, time_from=None, time_to=None):
    if data is not None:
        filtered_data = apply_filters(window, data.copy())

        if window.current_time_from is None or window.current_time_to is None:
            window.current_time_from = filtered_data['time'].min()
            window.current_time_to = filtered_data['time'].max()

        if window.canvas_frame and window.canvas.axes:
            current_xlim = window.canvas.axes.get_xlim()
        else:
            current_xlim = None

        if window.canvas_frame is None:
            print("Creating a new container for the canvas")
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

            layout_canvas = QVBoxLayout()
            window.canvas = MplCanvas(window.canvas_frame, width=8, height=6, dpi=100)
            layout_canvas.addWidget(window.canvas)
            window.canvas_frame.setLayout(layout_canvas)
            window.canvas_layout.addWidget(window.canvas_frame)
            print("The plot canvas has been created and added to the container")

        window.canvas.figure.clf()
        window.canvas.axes = window.canvas.figure.add_subplot(111)

        if time_from is not None and time_to is not None:
            window.canvas.axes.set_xlim(time_from, time_to)
        elif current_xlim:
            window.canvas.axes.set_xlim(current_xlim)
        else:
            window.canvas.axes.set_xlim(filtered_data['time'].min(), filtered_data['time'].max())

        visible_data = filtered_data[(filtered_data['time'] >= window.canvas.axes.get_xlim()[0]) &
                                     (filtered_data['time'] <= window.canvas.axes.get_xlim()[1])]
        if not visible_data.empty:
            min_y = visible_data['gradient.B'].min()
            max_y = visible_data['gradient.B'].max()
            data_range = max_y - min_y
            window.canvas.axes.set_ylim(min_y - data_range, max_y + data_range)

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

        window.canvas.axes.plot(filtered_data['time'], filtered_data['gradient.B'], label='Gradient B', color=line_color)

        overlay_series = compute_ecg_overlay_series(window, filtered_data)
        if overlay_series is not None:
            window.canvas.axes.plot(filtered_data['time'], overlay_series, label='ECG overlay', color='orange', linewidth=1.0, alpha=0.65)

        peaks = filtered_data.attrs.get('peaks')
        if isinstance(peaks, np.ndarray) and peaks.size:
            peak_times = filtered_data.iloc[peaks]['time']
            peak_values = filtered_data.iloc[peaks]['gradient.B']
            window.canvas.axes.scatter(peak_times, peak_values, color='magenta', s=25, label='Detected peaks', zorder=5)
        else:
            peaks = None

        window.canvas.axes.set_xlabel('Time')
        window.canvas.axes.set_ylabel('Magnetic Field (B)')
        window.canvas.axes.set_title('Magnetocardiogram Visualization')
        features = filtered_data.attrs.get('features', {})
        if hasattr(window, 'update_feature_summary'):
            window.update_feature_summary(features)

        handles, labels = window.canvas.axes.get_legend_handles_labels()
        if handles:
            window.canvas.axes.legend(handles, labels)

        window.canvas.draw()
        print("Plot updated successfully.")


def update_zoom(window, value):
    if window.current_time_from is None or window.current_time_to is None:
        return

    zoom_factor = (101 - value) / 100
    data_range = window.current_time_to - window.current_time_from
    visible_range = data_range * zoom_factor

    current_center = (window.canvas.axes.get_xlim()[0] + window.canvas.axes.get_xlim()[1]) / 2.0

    new_time_from = current_center - visible_range / 2.0
    new_time_to = current_center + visible_range / 2.0

    new_time_from = max(new_time_from, window.data['time'].min())
    new_time_to = min(new_time_to, window.data['time'].max())

    window.canvas.axes.set_xlim(new_time_from, new_time_to)

    filtered_data = apply_filters(window, window.data.copy())
    visible_data = filtered_data[(filtered_data['time'] >= new_time_from) &
                                 (filtered_data['time'] <= new_time_to)]

    min_y = visible_data['gradient.B'].min()
    max_y = visible_data['gradient.B'].max()

    if not visible_data.empty:
        data_range_y = max_y - min_y
        window.canvas.axes.set_ylim(min_y - data_range_y, max_y + data_range_y)

    print(min_y, max_y)

    if value < 101:
        window.pan_slider.setEnabled(True)
    else:
        window.pan_slider.setEnabled(False)

    window.canvas.draw()


def update_pan(window, value):
    if window.current_time_from is None or window.current_time_to is None:
        return

    pan_factor = value / 100.0
    current_xlim = window.canvas.axes.get_xlim()
    visible_range = current_xlim[1] - current_xlim[0]
    data_range = window.current_time_to - window.current_time_from

    pan_offset = pan_factor * (data_range - visible_range)
    new_time_from = window.current_time_from + pan_offset
    new_time_to = new_time_from + visible_range

    window.canvas.axes.set_xlim(new_time_from, new_time_to)

    filtered_data = apply_filters(window, window.data.copy())
    visible_data = filtered_data[(filtered_data['time'] >= new_time_from) &
                                 (filtered_data['time'] <= new_time_to)]

    min_y = visible_data['gradient.B'].min()
    max_y = visible_data['gradient.B'].max()

    if not visible_data.empty:
        data_range_y = max_y - min_y
        window.canvas.axes.set_ylim(min_y - data_range_y, max_y + data_range_y)

    print(min_y, max_y)

    window.canvas.draw()
