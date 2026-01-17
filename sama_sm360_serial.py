#!/usr/bin/env python3
"""
Sama SM360 LCD Driver - Serial Protocol (COM Port)
Based on captured Windows traffic
"""

import serial
import time
from typing import Optional

# Serial port configuration
BAUDRATE = 115200  # Sera confirmé
PACKET_SIZE = 250  # Taille observée dans les captures


class SamaSM360Serial:
    def __init__(self, port='COM4'):
        """
        Initialize Sama SM360 via serial port

        Args:
            port: COM port (Windows) or /dev/ttyACM0 (Linux)
        """
        self.port = port
        self.ser = None

    def connect(self):
        """Open serial connection"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=BAUDRATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=2,
                write_timeout=2
            )

            # Set RTS/DTR (observed in capture)
            self.ser.setRTS(True)
            self.ser.setDTR(True)

            time.sleep(0.1)
            print(f"✓ Connected to {self.port} at {BAUDRATE} baud")
            return True

        except serial.SerialException as e:
            print(f"✗ Failed to connect: {e}")
            return False

    def _build_packet(self, cmd: int, subcmd: int, value: int = 0) -> bytes:
        """
        Build packet based on captured format

        Structure observée:
        [0]    = Command byte
        [1-2]  = 0xef 0x69 (magic header)
        [3-5]  = 0x00 0x00 0x00
        [6]    = Subcommand
        [7-9]  = 0x00 0x00 0x00
        [10]   = Value
        [11+]  = Padding (0x00)
        """
        packet = bytearray(PACKET_SIZE)
        packet[0] = cmd
        packet[1] = 0xef
        packet[2] = 0x69
        packet[3:6] = b'\x00\x00\x00'
        packet[6] = subcmd
        packet[7:10] = b'\x00\x00\x00'
        packet[10] = value & 0xFF
        # Rest is already 0x00

        return bytes(packet)

    def _read_response(self, timeout=1.0) -> Optional[bytes]:
        """Read response from LCD"""
        old_timeout = self.ser.timeout
        self.ser.timeout = timeout

        try:
            # Attendre des données
            if self.ser.in_waiting > 0 or timeout > 0:
                response = self.ser.read(1024)  # Lire jusqu'à 1KB
                if response:
                    return response
        except Exception as e:
            print(f"Read error: {e}")
        finally:
            self.ser.timeout = old_timeout

        return None

    def initialize(self) -> bool:
        """
        Initialize LCD with captured init sequence
        """
        print("🔧 Initializing Sama SM360...")

        try:
            # Packet #60 - Init command (observed: 0x01 ef 69 ...)
            init_packet = self._build_packet(
                cmd=0x01,
                subcmd=0x01,
                value=0x00
            )
            init_packet = bytearray(init_packet)
            init_packet[10] = 0xc5  # Observed value
            init_packet[11] = 0xd3  # Observed value

            self.ser.write(bytes(init_packet))
            print("  ✓ Init packet sent")
            time.sleep(0.1)

            # Read device identification
            response = self._read_response(timeout=0.5)
            if response:
                try:
                    device_id = response.decode('utf-8', errors='ignore').strip('\x00')
                    print(f"  ✓ Device ID: {device_id}")
                except:
                    print(f"  ✓ Device responded: {response.hex()[:40]}...")

            # Packet #100 - Secondary init
            init2 = self._build_packet(cmd=0x79, subcmd=0x01, value=0x00)
            self.ser.write(init2)
            time.sleep(0.05)
            print("  ✓ Secondary init sent")

            # Packet #141 - Third init
            init3 = self._build_packet(cmd=0x96, subcmd=0x01, value=0x00)
            self.ser.write(init3)
            time.sleep(0.05)
            print("  ✓ Third init sent")

            print("✅ Initialization complete!")
            return True

        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False

    def set_brightness(self, brightness: int) -> bool:
        """
        Set LCD brightness

        Args:
            brightness: 0-100
        """
        if not 0 <= brightness <= 100:
            raise ValueError("Brightness must be 0-100")

        # Convert 0-100 to 0-255
        value = int((brightness / 100.0) * 255)

        try:
            # Packet #196 pattern: 0x7b ef 69 00 00 00 01 00 00 00 [VALUE]
            packet = self._build_packet(cmd=0x7b, subcmd=0x01, value=value)

            self.ser.write(packet)
            print(f"  ✓ Brightness set to {brightness}% (0x{value:02x})")

            # Check response
            response = self._read_response(timeout=0.2)
            if response:
                print(f"  ✓ Device acknowledged")

            return True

        except Exception as e:
            print(f"  ✗ Failed to set brightness: {e}")
            return False

    def send_command(self, cmd: int, subcmd: int = 0x01, value: int = 0) -> bool:
        """
        Send generic command to LCD

        Args:
            cmd: Command byte
            subcmd: Subcommand byte
            value: Value byte
        """
        try:
            packet = self._build_packet(cmd, subcmd, value)
            self.ser.write(packet)
            print(f"  ✓ Command sent: cmd=0x{cmd:02x} subcmd=0x{subcmd:02x} value=0x{value:02x}")

            response = self._read_response(timeout=0.2)
            if response:
                print(f"  ✓ Response: {response[:40]}")
                return True
            return True

        except Exception as e:
            print(f"  ✗ Failed to send command: {e}")
            return False

    def get_status(self) -> Optional[dict]:
        """
        Get device status (monitoring values)
        Based on packet #287 response
        """
        try:
            # Send status request (pattern from packet #255)
            status_req = self._build_packet(cmd=0x64, subcmd=0x01, value=0x00)
            self.ser.write(status_req)

            # Read response
            response = self._read_response(timeout=0.5)
            if response:
                try:
                    # Try to parse as text (observed: "2688-1420-1268-...")
                    text = response.decode('utf-8', errors='ignore').strip('\x00')
                    if '-' in text:
                        values = text.split('-')
                        return {
                            'raw': text,
                            'values': [int(v) for v in values if v.isdigit()]
                        }
                except:
                    pass

                return {'raw_hex': response.hex()}

            return None

        except Exception as e:
            print(f"Error getting status: {e}")
            return None

    def close(self):
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("✅ Port closed")


def test_display_commands(lcd):
    """Test various commands to activate display"""
    print("\n🧪 Testing display activation commands...")

    # Test différentes commandes observées
    test_cmds = [
        (0x7d, 0x05, 0x80, "Type 5 command (from capture)"),
        (0x7d, 0x01, 0x80, "Type 5 variant"),
        (0x96, 0x01, 0x01, "Init variant with value"),
        (0x64, 0x01, 0x01, "Status variant"),
        (0x01, 0x01, 0x01, "Init with value 1"),
        (0x79, 0x01, 0x01, "Secondary init variant"),
    ]

    for cmd, subcmd, value, desc in test_cmds:
        print(f"\nTesting: {desc}")
        lcd.send_command(cmd, subcmd, value)
        time.sleep(0.5)

        # Check for response
        response = lcd._read_response(timeout=0.3)
        if response:
            try:
                text = response.decode('utf-8', errors='ignore').strip('\x00')
                if text:
                    print(f"  Response (text): {text[:50]}")
            except:
                print(f"  Response (hex): {response[:20].hex()}")


def main():
    """Test the driver"""
    print("=" * 60)
    print("Sama SM360 LCD Driver - Serial Protocol")
    print("=" * 60)

    # Detect COM port
    import serial.tools.list_ports

    ports = list(serial.tools.list_ports.comports())
    sama_port = None

    print("\nAvailable COM ports:")
    for port in ports:
        print(f"  {port.device}: {port.description}")
        if '1A86' in port.hwid or '1D6B' in port.hwid:
            sama_port = port.device
            print(f"    ^ Detected Sama SM360!")

    if not sama_port:
        print("\n⚠ Sama SM360 not auto-detected")
        sama_port = input("Enter COM port (e.g., COM4): ").strip() or 'COM4'

    try:
        lcd = SamaSM360Serial(sama_port)

        if not lcd.connect():
            print("\n❌ Failed to connect")
            return

        if not lcd.initialize():
            print("\n❌ Failed to initialize")
            return

        print("\n🔆 Testing brightness control...")
        for level in [100, 50, 100]:
            lcd.set_brightness(level)
            time.sleep(0.5)

        # Test display activation
        test_display_commands(lcd)

        print("\n📊 Getting device status...")
        status = lcd.get_status()
        if status:
            print(f"Status: {status}")

        print("\n💡 Keeping brightness at 100% for 10 seconds...")
        lcd.set_brightness(100)
        print("   Watch the screen - does anything appear?")
        time.sleep(10)

        print("\n✅ Tests complete!")
        lcd.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main() 