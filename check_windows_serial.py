import serial
import serial.tools.list_ports
import time

# Global variables to store the parsed values
value1 = 0
value2 = 0
value3 = 0


def find_arduino_port():
    """Try to automatically find the Arduino COM port"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'arduino' in port.description.lower() or 'ch340' in port.description.lower():
            return port.device
    return None


def parse_serial_data(data_string):
    """
    Parse the incoming data string into three integers
    Format expected: "int1,int2,int3"
    """
    global value1, value2, value3
    try:
        # Split the string by commas and convert to integers
        parts = data_string.split(',')
        if len(parts) == 3:
            value1 = int(parts[0])
            value2 = int(parts[1])
            value3 = int(parts[2])
            return True
        else:
            print(f"Warning: Expected 3 values, got {len(parts)}")
            return False
    except ValueError as e:
        print(f"Error parsing data: {e}")
        return False


def read_serial_data(port_name, baud_rate=57600):
    """
    Read data from the specified serial port and update global variables
    """
    global value1, value2, value3

    try:
        ser = serial.Serial(port_name, baud_rate, timeout=1)
        print(f"Connected to {port_name} at {baud_rate} baud")
        print("Press Ctrl+C to stop reading...\n")

        while True:
            if ser.in_waiting > 0:
                data = ser.readline().decode('utf-8').strip()
                if parse_serial_data(data):
                    # Print the updated values (optional)
                    print(f"Updated values: {value1}, {value2}, {value3}")

            # Add your code here that uses the updated values
            # Example: process_values(value1, value2, value3)

            time.sleep(0.01)

    except serial.SerialException as e:
        print(f"Serial connection error: {e}")
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print("Serial connection closed")


if __name__ == "__main__":
    arduino_port = find_arduino_port()

    if arduino_port:
        print(f"Found Arduino at {arduino_port}")
        read_serial_data(arduino_port)
    else:
        print("Could not automatically find Arduino port.")
        port_name = input("Please enter the COM port (e.g., COM3): ")
        baud_rate = int(input("Enter baud rate (default 9600): ") or "9600")
        read_serial_data(port_name, baud_rate)