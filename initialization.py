import os
from datetime import datetime
import tio
from pprint import pprint

session = tio.TIOSession(url="COM6", verbose=False, specialize=False)

session.specialize()
print(session.rpc("dev.desc").decode('utf-8'))
print(session.rpc("data.send_all"))

record_start_time = datetime.now()
recorded_data = []
file_path = os.path.join(os.getcwd(), "data.csv")

for n in range(0, 50000):
    decoded_packet = session.pub_queue.get(timeout=1)
    if decoded_packet["type"] == tio.TL_PTYPE_STREAM0:
        timestamp, values = session.protocol.stream_data(decoded_packet, timeaxis=True)
        recorded_data.append((timestamp, values))
        print(timestamp, values)

if recorded_data:
    currenttime = datetime.now().strftime("%H:%M:%S.%f")

    with open(file_path, "w") as file:
        file.write("Czas, Wartość\n")
        for timestamp, value in recorded_data:
            file.write(f"{currenttime},{value[-1]}\n")
            print(f"Dane zapisano w pliku: {file_path}")