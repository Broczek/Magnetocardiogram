from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QVBoxLayout, QFrame
from scipy.signal import butter, filtfilt


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        self.setStyleSheet("background-color: transparent;")


def show_time_range_controls(window):
    window.time_range_label.show()
    window.time_from_input.show()
    window.time_to_input.show()
    window.set_time_button.show()
    window.zoom_label.show()
    window.zoom_slider.show()
    window.pan_label.show()
    window.pan_slider.show()
    window.filters_label.show()
    window.lowpass_filter.show()
    window.highpass_filter.show()
    window.filter_50hz.show()
    window.filter_100hz.show()
    window.filter_150hz.show()
    window.custom_filter_1_input.show()
    window.custom_filter_1_apply.show()
    window.custom_filter_2_input.show()
    window.custom_filter_2_apply.show()
    window.setFixedSize(1200, 850)


def validate_custom_filter(input_field, apply_checkbox):
    text = input_field.text()
    if text.isdigit() and 1 <= int(text) <= 999:
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


def lowpass_filter(data, cutoff=0.1, fs=1.0, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = filtfilt(b, a, data)
    return y


def highpass_filter(data, cutoff=0.1, fs=1.0, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='high', analog=False)
    y = filtfilt(b, a, data)
    return y


def notch_filter(data, freq, fs=1000.0, Q=30.0):
    from scipy.signal import iirnotch
    nyq = 0.5 * fs
    w0 = freq / nyq
    if w0 >= 1:
        raise ValueError(f"Częstotliwość filtru {freq}Hz przekracza Nyquista dla fs={fs}Hz.")

    b, a = iirnotch(w0, Q)
    y = filtfilt(b, a, data)
    return y


def apply_filters(window, data):
    if window.lowpass_filter.isChecked():
        print("Applying Lowpass Filter...")
        data['gradient.B'] = lowpass_filter(data['gradient.B'])

    if window.highpass_filter.isChecked():
        print("Applying Highpass Filter...")
        data['gradient.B'] = highpass_filter(data['gradient.B'])

    if window.filter_50hz.isChecked():
        print("Applying 50Hz Notch Filter...")
        data['gradient.B'] = notch_filter(data['gradient.B'], freq=50)

    if window.filter_100hz.isChecked():
        print("Applying 100Hz Notch Filter...")
        data['gradient.B'] = notch_filter(data['gradient.B'], freq=100)

    if window.filter_150hz.isChecked():
        print("Applying 150Hz Notch Filter...")
        data['gradient.B'] = notch_filter(data['gradient.B'], freq=150)

    try:
        custom_freq_1 = int(window.custom_filter_1_input.text())
        if window.custom_filter_1_apply.isChecked() and 1 <= custom_freq_1 <= 999:
            print(f"Applying Custom Filter 1 with freq {custom_freq_1}Hz...")
            data['gradient.B'] = notch_filter(data['gradient.B'], freq=custom_freq_1)
    except ValueError:
        print("Invalid input for Custom Filter 1.")

    try:
        custom_freq_2 = int(window.custom_filter_2_input.text())
        if window.custom_filter_2_apply.isChecked() and 1 <= custom_freq_2 <= 999:
            print(f"Applying Custom Filter 2 with freq {custom_freq_2}Hz...")
            data['gradient.B'] = notch_filter(data['gradient.B'], freq=custom_freq_2)
    except ValueError:
        print("Invalid input for Custom Filter 2.")

    return data


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

            layout_canvas = QVBoxLayout()
            window.canvas = MplCanvas(window.canvas_frame, width=8, height=6, dpi=100)
            layout_canvas.addWidget(window.canvas)
            window.canvas_frame.setLayout(layout_canvas)

            window.canvas_layout.addWidget(window.canvas_frame)
            print("Płótno wykresu zostało stworzone i dodane do kontenera.")

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
            window.canvas.axes.set_ylim(min_y, max_y)

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
        window.canvas.axes.set_xlabel('Time')
        window.canvas.axes.set_ylabel('Magnetic Field (B)')
        window.canvas.axes.set_title('Magnetocardiogram Visualization')
        window.canvas.axes.legend()

        window.canvas.draw()
        print("Plot updated successfully.")


def update_zoom(window, value):
    if window.current_time_from is None or window.current_time_to is None:
        return

    zoom_factor = value / 100.0
    data_range = window.current_time_to - window.current_time_from
    visible_range = data_range * zoom_factor

    current_center = (window.canvas.axes.get_xlim()[0] + window.canvas.axes.get_xlim()[1]) / 2.0

    new_time_from = current_center - visible_range / 2.0
    new_time_to = current_center + visible_range / 2.0

    new_time_from = max(new_time_from, window.data['time'].min())
    new_time_to = min(new_time_to, window.data['time'].max())

    window.canvas.axes.set_xlim(new_time_from, new_time_to)

    visible_data = window.data[(window.data['time'] >= new_time_from) &
                               (window.data['time'] <= new_time_to)]

    if not visible_data.empty:
        min_y = visible_data['gradient.B'].min()
        max_y = visible_data['gradient.B'].max()
        window.canvas.axes.set_ylim(min_y, max_y)

    if value < 100:
        window.pan_slider.setEnabled(True)
    else:
        window.pan_slider.setEnabled(False)

    window.canvas.draw()


def update_pan(window, value):
    if window.current_time_from is None or window.current_time_to is None:
        return

    pan_factor = value / 100.0
    data_range = window.current_time_to - window.current_time_from
    zoom_factor = window.zoom_slider.value() / 100.0
    visible_range = data_range * zoom_factor

    pan_offset = pan_factor * (data_range - visible_range)
    new_time_from = window.current_time_from + pan_offset
    new_time_to = new_time_from + visible_range

    window.canvas.axes.set_xlim(new_time_from, new_time_to)

    visible_data = window.data[(window.data['time'] >= new_time_from) &
                               (window.data['time'] <= new_time_to)]

    if not visible_data.empty:
        min_y = visible_data['gradient.B'].min()
        max_y = visible_data['gradient.B'].max()
        window.canvas.axes.set_ylim(min_y, max_y)

    window.canvas.draw()
