import serial
from tio_protocol import TIOProtocol, TL_PTYPE_STREAM0
from slip import SLIP_END_CHAR, decode
import time

def initialize_sensor(port="COM6", baudrate=115200, data_queue=None):
    try:
        print("Inicjalizacja połączenia...")

        ser = serial.Serial(port, baudrate=baudrate, timeout=0.1)
        ser.reset_input_buffer()

        protocol = TIOProtocol()

        packet_rpc = b'\xc0\x02\x00\x0c\x00g\x9d\x08\x80data.format\x86Gq~\xc0'
        ser.write(packet_rpc)
        response = ser.read(64)
        print(f"Odpowiedź RPC: {response}")

        sampling_rate_rpc = b'\xc0\x02\x00\x0c\x00g\x9d\x08\x80data.rate\x86Gq~\xc0'
        ser.write(sampling_rate_rpc)
        response = ser.read(64)
        print(f"Ustawiono częstotliwość próbkowania: {response}")

        return ser, protocol, data_queue

    except Exception as e:
        print(f"Błąd podczas inicjalizacji sensora: {e}")
        return None, None, None


def read_data(ser, protocol, data_queue):
    buffer = bytearray()

    try:
        while True:
            data = ser.read(ser.in_waiting or 64)
            buffer.extend(data)

            while SLIP_END_CHAR in buffer:
                try:
                    packet, buffer = buffer.split(SLIP_END_CHAR, 1)
                    decoded_packet = protocol.decode_packet(decode(packet))

                    if decoded_packet["type"] == TL_PTYPE_STREAM0:
                        timestamp, values = protocol.stream_data(decoded_packet, timeaxis=True)
                        if data_queue:
                            data_queue.put((timestamp, values))
                    else:
                        print(f"Nierozpoznany typ pakietu: {decoded_packet['type']}")

                except Exception as e:
                    print(f"Błąd dekodowania pakietu: {e}")
            time.sleep(0.005)
    except KeyboardInterrupt:
        print("Zakończono odczyt danych.")
    except Exception as e:
        print(f"Błąd w read_data: {e}")
    finally:
        ser.close()