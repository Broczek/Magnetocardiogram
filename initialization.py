import matplotlib.pyplot as plt

# Struktura aplikacji
struktura = {
    "Aplikacja": {
        "GUI.py": {
            "class MainWindow": [
                "__init__ – konstruktor",
                "changeEvent – obsługa zmiany stanu okna",
                "start_file_analysis – uruchomienia okna analizy danych z pliku",
                "start_real_time_analysis – uruchomienie okna wizualizacji sygnału na żywo",
                "reset_real_time_window – reset stanu okna wizualizacji sygnału na żywo",
                "show_controls – ewolucja okna bazowego",
                "reset_controls_to_default – reset stanu okna analizy danych z pliku",
                "change_theme – zmiana szaty graficznej (dark mode)"
            ]
        },
        "backend.py": {
            "class MplCanvas": [],
            "Funkcje": [
                "detect_sensor_port – automatyczne wykrycie portu sensora",
                "state_change – obsługa zmiany stanu aplikacji",
                "show_controls – wyświetlanie przycisków",
                "validate_custom_filter – walidacja parametrów filtrów konfigurowalnych",
                "validate_input – walidacja danych wejściowych od użytkownika",
                "apply_time_range – aplikacja wybranego okna czasowego na dane",
                "bandpass_filter – konfigurowalny filtr pasmowozaporowy",
                "lowpass_filter – filtr dolnoprzepustowy",
                "highpass_filter – filtr górnoprzepustowy",
                "notch_filter – zdefiniowany filtr pasmowozaporowy",
                "update_bandpass_filter – aktualizacja parametrów filtra pasmowoprzepustowego",
                "handle_bandpass_apply_toggle – obsługa przełączania filtra pasmowoprzepustowego",
                "update_slider_labels – aktualizacja etykiet suwaka filtra pasmowoprzepustowego",
                "validate_bandpass_values – walidacja wartości filtra pasmowoprzepustowego",
                "apply_filters – zastosowanie wybranych filtrów",
                "toggle_bandpass_apply_silently – zabezpieczenie błędnej aktualizacji filtra pasmowoprzepustowego",
                "handle_filter_toggle – obsługa przełączania filtrów",
                "save_data – zapis danych do pliku",
                "update_plot – aktualizacji wizualizacji danych",
                "update_zoom – przybliżanie wykresu",
                "update_pan – przesuwanie wykresu"
            ]
        },
        "data_processing.py": [
            "load_data – wczytanie danych z pliku",
            "aggregate_duplicate_timestamps – zabezpieczenie przed próbkami zduplikowanymi w czasie",
            "load_and_plot_file – wczytanie i przygotowanie danych do wizualizacji"
        ],
        "live_visualization.py": {
            "class CustomTIOSession": ["recv_slip_packet – nadpisanie metody"],
            "class RealTimePlotWindow": [
                "__init__ – konstruktor",
                "changeEvent – obsługa zmiany stanu okna",
                "toggle_lowpass – przełączania filtra dolnoprzepustowego",
                "toggle_highpass – przełączanie filtra górnoprzepustowego",
                "toggle_notch – przełączanie filtra 50 Hz",
                "toggle_custom – przełączania konfigurowalnego filtra pasmowozaporowego",
                "change_theme – zmiana szaty graficznej okna (dark mode)",
                "start_recording – rozpoczęcie akwizycji danych do pliku",
                "stop_recording – zakończenie rejestracji danych",
                "closeEvent – obsługa zamykania okna"
            ],
            "class RealTimePlotCanvas": [
                "__init__ – konstruktor",
                "add_data – aktualizacja tablicy danych",
                "update_plot – aktualizacja wykresu na bieżąco z możliwą filtracją",
                "start_data_loop – uruchomienie procesu odbioru danych",
                "stop_data_loop – zatrzymanie procesu odbioru danych",
                "data_loop – proces odbioru i przetwarzania danych z sensora",
                "set_dark_mode – zmiana szaty graficznej wykresu (dark mode)",
                "resizeEvent – obsługa zmiany rozmiaru okna"
            ],
            "Funkcje": ["reset_com_port – reset portu szeregowego sensora"]
        },
        "main.py – moduł uruchomienia aplikacji": {},
        "requirements.txt – Wymagane biblioteki": {},
        "build_app.bat – Skrypt przeznaczony do budowy pliku .exe": {},
        "main.spec – Specyfikacja kompilacji": {},
        "devcon.exe – Narzędzie wiersza poleceń systemu Windows do zarządzania urządzeniami": {},
        "folder images – Zasoby graficzne aplikacji": {}
    }
}


# Funkcja do generowania tekstu drzewa
def create_tree_text(structure, indent="", last=True):
    lines = []
    for i, (key, value) in enumerate(structure.items()):
        is_last = i == (len(structure) - 1)
        prefix = "└── " if last else "├── "
        lines.append(f"{indent}{prefix}{key}")
        if isinstance(value, dict):
            extension = "    " if last else "│   "
            lines += create_tree_text(value, indent + extension, is_last)
        elif isinstance(value, list):
            extension = "    " if last else "│   "
            for j, item in enumerate(value):
                item_prefix = "└── " if j == len(value) - 1 else "├── "
                lines.append(f"{indent}{extension}{item_prefix}{item}")
    return lines


# Generowanie diagramu
tree_lines = create_tree_text(struktura)

# Rysowanie diagramu
plt.figure(figsize=(12, len(tree_lines) * 0.21))
plt.text(0, 1, "\n".join(tree_lines), fontsize=10, fontfamily='monospace', verticalalignment='top')
plt.axis('off')
plt.tight_layout()

# Zapis do pliku
diagram_path = 'graph.png'
plt.savefig(diagram_path, bbox_inches='tight')
plt.close()

diagram_path
