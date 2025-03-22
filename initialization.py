import serial
import struct
import time


class DeviceManual:
    def __init__(self, port="COM6", baudrate=115200):
        self.serial = serial.Serial(port, baudrate=baudrate, timeout=1)
        self.serial.reset_input_buffer()
        print("Połączenie z urządzeniem zainicjalizowane.")

    def send_rpc(self, rpc_name, rpc_type, value=None):
        rpc_packet = bytearray()
        rpc_packet += struct.pack('<H', len(rpc_name))
        rpc_packet += rpc_name.encode('utf-8')
        rpc_packet += struct.pack('<B', rpc_type)
        if value is not None:
            rpc_packet += struct.pack('<f', value)
        self.serial.write(rpc_packet)
        response = self.serial.readline()
        print(f"Odpowiedź RPC: {response}")

    def configure_binary_mode(self):
        print("Przełączanie urządzenia w tryb binarny...")
        init_packet = bytearray(b'\xc0\x02\x00\x0c\x00g\x9d\x08\x80dev.desc\x86Gq~\xc0')
        self.serial.write(init_packet)
        time.sleep(0.1)
        response = self.serial.readline()
        print(f"Odpowiedź z urządzenia: {response.decode(errors='ignore')}")

    def read_data(self):
        buffer = bytearray()
        while True:
            data = self.serial.read(self.serial.in_waiting or 64)
            buffer.extend(data)
            if b'\xc0' in buffer:
                packet, buffer = buffer.split(b'\xc0', 1)
                print(f"Odebrany pakiet: {packet}")

    def close(self):
        self.serial.close()
        print("Połączenie zamknięte.")


if __name__ == "__main__":
	device = DeviceManual(port="COM6", baudrate=115200)

	print("Przełączam urządzenie w tryb binarny...")
	device.configure_binary_mode()

	print("Odczyt danych z urządzenia...")
	try:
		device.read_data()
	except KeyboardInterrupt:
		print("Przerwano testowanie.")
	finally:
		device.close()
