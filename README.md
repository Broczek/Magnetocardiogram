# Magnetocardiogram (MCG) Signal Visualization and Analysis

An application for visualizing and analyzing magnetocardiographic signals, developed based on an innovative device from Twinleaf. This solution represents a significant step forward in portable MCG testing, as part of the work presented at the 31st Conference of the Association of Non-Invasive Electrocardiology and Telemetry of the Polish Cardiac Society in Zakopane.

## Features

The application offers two main modes of operation: file data analysis and real-time signal monitoring.

* **File Data Analysis**:
    * Load data from various file formats (.txt, .tsv, .csv).
    * Interactive plot visualization with zooming and panning capabilities.
    * Ability to specify the time range for analysis.
    * Save processed data to `.txt`, `.tsv`, and `.xlsx` files.

* **Real-Time Monitoring**:
    * Live visualization of the MCG signal directly from the sensor.
    * Ability to record and save real-time sessions.

* **Signal Filtering**:
    * Advanced signal filters, including:
        * Lowpass filter
        * Highpass filter
        * Notch filter for 50Hz, 100Hz, and 150Hz frequencies.
        * Two configurable Notch filters in the 1-230Hz range.
        * Bandpass filter with an interactive slider for range selection.

* **User Interface**:
    * Modern and intuitive graphical user interface.
    * Ability to switch between light and dark themes.

## Technical Details

The application is written in **Python** using the **PyQt5** library for the graphical user interface. Data handling and manipulation are done with the **pandas** library, and visualization is handled by **matplotlib**. Advanced signal operations, such as filtering, are implemented using the **scipy** library.
