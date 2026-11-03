#!/usr/bin/env python3
"""Sets the DS3231 clock of the Smart Attendance System to the PC's current time, over the serial (COM) port.
The main firmware must be running (it understands the SETTIME command). Close the serial monitor first: only one
program can use the port at a time.

Run with PlatformIO's Python (it already has pyserial):
    ~/.platformio/penv/bin/python firmware/tools/set_clock.py            # finds the port by itself
    ~/.platformio/penv/bin/python firmware/tools/set_clock.py /dev/ttyACM0
"""
import sys
import time
from datetime import datetime

import serial
from serial.tools import list_ports


def find_port():
    """The COM port of the board: the CH343 / CH340 / CP210x serial chip, else the first ttyACM / ttyUSB / COM port."""
    ports = list(list_ports.comports())
    for p in ports:
        if p.vid in (0x1A86, 0x10C4):            # QinHeng CH34x, Silicon Labs CP210x
            return p.device
    for p in ports:
        if 'ACM' in p.device or 'USB' in p.device or p.device.upper().startswith('COM'):
            return p.device
    return None


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_port()
    if not port:
        sys.exit('No serial port found: plug the cable into the port marked COM.')
    ser = serial.Serial()
    ser.port, ser.baudrate, ser.timeout = port, 115200, 0.2
    ser.dtr = ser.rts = False                    # do not reset the board when the port opens
    try:
        ser.open()
    except serial.SerialException as e:
        sys.exit(f'Cannot open {port}: {e}\nClose the serial monitor (only one program can use the port).')
    time.sleep(2.5)                              # in case the board restarted anyway: let it boot
    ser.reset_input_buffer()
    for attempt in range(3):
        now = datetime.now()
        if now.microsecond > 900000:             # send close to the start of a second
            time.sleep(0.1)
            now = datetime.now()
        cmd = now.strftime('SETTIME %Y-%m-%d %H:%M:%S')
        ser.write((cmd + '\n').encode())
        answer, t0 = '', time.time()
        while time.time() - t0 < 2.0:
            answer += ser.read(256).decode(errors='replace')
            if 'Clock set to' in answer:
                line = answer[answer.index('Clock set to'):].splitlines()
                print(f'{port}: sent "{cmd}" -> {" ".join(line[:2]).strip()}')
                ser.close()
                return
        time.sleep(1.0)
    ser.close()
    sys.exit(f'No answer from the board on {port}. Is the main firmware running? Answer received: {answer.strip()[:200]!r}')


if __name__ == '__main__':
    main()
