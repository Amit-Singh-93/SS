import serial
import serial.tools.list_ports
import time

# Global variables to store parsed data
int1 = 0
int2 = 0
int3 = 0
float_val = 0.0
char_val = ''
valid_data_count = 0
error_count = 0
ser = None


def find_arduino_port():
    """Try to automatically find the Arduino COM port"""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if 'arduino' in port.description.lower() or 'ch340' in port.description.lower():
            return port.device
    return None


def connect_serial(port_name=None, baud_rate=57600):
    """Establish serial connection"""
    global ser

    if port_name is None:
        port_name = find_arduino_port()
        if port_name is None:
            print("Arduino port not found automatically")
            return False

    try:
        ser = serial.Serial(port_name, baud_rate, timeout=1)
        print(f"Connected to {port_name} at {baud_rate} baud")
        print("Waiting for data in format: $int1,int2,int3,float.2,char1\\n")
        return True
    except serial.SerialException as e:
        print(f"Connection error: {e}")
        return False


def parse_data(data_string):
    """
    Parse data in format "$int1,int2,int3,float.2,char1"
    Returns True if parsing was successful
    """
    global int1, int2, int3, float_val, char_val, valid_data_count, error_count

    try:
        # Remove $ and \n if present
        clean_data = data_string.strip().replace('$', '')
        if not clean_data:
            return False

        parts = clean_data.split(',')
        if len(parts) != 5:
            print(f"Error: Expected 5 values, got {len(parts)}")
            error_count += 1
            return False

        # Parse each component
        int1 = int(parts[0])
        int2 = int(parts[1])
        int3 = int(parts[2])
        float_val = float(parts[3])
        char_val = parts[4][0] if parts[4] else ''  # Take first character only

        valid_data_count += 1
        return True

    except ValueError as e:
        print(f"Parsing error: {e} - Data: {data_string}")
        error_count += 1
        return False


def display_current_values():
    """Display the current parsed values"""
    print(f"Values: int1={int1}, int2={int2}, int3={int3}, "
          f"float={float_val:.2f}, char='{char_val}'")


def close_serial():
    """Close the serial connection"""
    global ser
    if ser and ser.is_open:
        ser.close()
        print("Serial connection closed")
    print(f"Summary: {valid_data_count} valid packets, {error_count} errors")


def main():
    # Try automatic connection first
    if not connect_serial(baud_rate=57600):
        # Manual connection if automatic fails
        port_name = input("Enter COM port (e.g., COM3): ")
        baud_rate = int(input("Enter baud rate (default 57600): ") or "57600")
        if not connect_serial(port_name, baud_rate):
            exit(1)

    try:
        while True:
            if ser.in_waiting > 0:
                data = ser.readline().decode('utf-8').strip()
                if data.startswith('$'):
                    if parse_data(data):
                        display_current_values()

            # Add your custom processing here
            # Example: process_data()

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStopping data reading...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        close_serial()


if __name__ == "__main__":
    main()