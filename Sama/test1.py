#!/usr/bin/env python3
"""
Sama SM360 LCD AIO Driver - Reverse Engineered
Based on USB packet sniffing
"""

import usb.core
import usb.util
import struct
import time
from typing import Optional

# Device IDs
VENDOR_ID = 0x1A86
PRODUCT_ID = 0xCA21

# Endpoints (à confirmer sous Linux avec lsusb -v)
ENDPOINT_BULK_OUT = 0x01
ENDPOINT_BULK_IN = 0x81
ENDPOINT_INTERRUPT_IN = 0x84


class SamaSM360:
    def __init__(self):
        """Initialize connection to Sama SM360 LCD AIO"""
        self.dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)

        if self.dev is None:
            raise ValueError("Sama SM360 not found. Check USB connection.")

        # Detach kernel driver if active
        for interface in [0, 1]:
            if self.dev.is_kernel_driver_active(interface):
                try:
                    self.dev.detach_kernel_driver(interface)
                    print(f"✅ Detached kernel driver from interface {interface}")
                except usb.core.USBError as e:
                    print(f"⚠️  Could not detach kernel driver: {e}")

        # Set configuration
        try:
            self.dev.set_configuration()
            print("✅ Device configured")
        except usb.core.USBError as e:
            print(f"⚠️  Configuration error: {e}")

    def _build_packet(self, cmd_type: int, command: int, params: bytes, flags: bytes = b'\x00\x00') -> bytes:
        """
        Build standard Sama packet format

        Structure observed:
        [00-01] Length (little-endian)
        [02-03] Command type (0x1050, 0x4015, 0x6035, etc.)
        [04-07] Timestamp/Sequence (set to 0 for simplicity)
        [08-09] Fixed: ff ff
        [0A-0B] Padding: 00 00
        [0C-0D] Flags (00 00, 01 c0, etc.)
        [0E-0F] Payload length
        [10+]   Payload data
        """
        payload = struct.pack('B', command) + params
        payload_len = len(payload)
        total_len = 0x10 + payload_len

        packet = struct.pack('<H', total_len)  # Length
        packet += struct.pack('<H', cmd_type)  # Command type
        packet += b'\x00\x00\x00\x00'  # Timestamp (simplified)
        packet += b'\xff\xff'  # Fixed
        packet += b'\x00\x00'  # Padding
        packet += flags  # Flags
        packet += struct.pack('<H', payload_len)  # Payload length
        packet += payload

        return packet

    def initialize(self):
        """Full initialization sequence based on sniffed packets"""

        print("🔧 Initializing Sama SM360...")

        try:
            # Step 1: Initial handshake (P#1 - BULK)
            handshake = self._build_packet(
                cmd_type=0x1050,
                command=0x00,
                params=b'\x02\x00\x0a\x00\x81\x03\x00\x00\x00\x00'
            )
            self.dev.write(ENDPOINT_BULK_OUT, handshake)
            time.sleep(0.1)
            print("  ✓ Handshake sent")

            # Step 2: HID GET_REPORT (P#3 - CONTROL IN)
            try:
                response = self.dev.ctrl_transfer(
                    bmRequestType=0xa1,  # Device-to-Host, Class, Interface
                    bRequest=0x01,  # GET_REPORT
                    wValue=0x0800,  # Feature Report
                    wIndex=0,
                    data_or_wLength=7
                )
                print(f"  ✓ Status read: {response.hex()}")
            except usb.core.USBError:
                print("  ⚠️  GET_REPORT failed (might be normal)")

            # Step 3: Main init command (P#4 - CONTROL OUT) - sent twice
            init_payload = bytes.fromhex("01 02 00 0a 00 80 02 07 00 00 00 03 00 c2 01 00 00 00 08")

            for i in range(2):
                try:
                    self.dev.ctrl_transfer(
                        bmRequestType=0x21,  # Host-to-Device, Class, Interface
                        bRequest=0x09,  # SET_REPORT
                        wValue=0x0200,
                        wIndex=0,
                        data_or_wLength=init_payload
                    )
                    print(f"  ✓ Init command #{i + 1} sent")
                    time.sleep(0.05)

                    # Read status between
                    if i == 0:
                        try:
                            self.dev.ctrl_transfer(0xa1, 0x01, 0x0800, 0, 7)
                        except:
                            pass
                except usb.core.USBError as e:
                    print(f"  ⚠️  Init command #{i + 1} failed: {e}")

            # Step 4: Confirmation with flag 01 c0 (P#7 - BULK)
            confirm = self._build_packet(
                cmd_type=0x1050,
                command=0x01,
                params=b'\x02\x00\x0a\x00\x81\x03\x00\x00\x00\x00',
                flags=b'\x01\xc0'
            )
            self.dev.write(ENDPOINT_BULK_OUT, confirm)
            time.sleep(0.1)
            print("  ✓ Confirmation sent")

            # Step 5: Final SET_REPORT (P#9)
            try:
                self.dev.ctrl_transfer(
                    bmRequestType=0x21,
                    bRequest=0x09,
                    wValue=0x0002,
                    wIndex=0,
                    data_or_wLength=bytes.fromhex("00 02 00 0a 00 00 02 08 00 00 00 00")
                )
                print("  ✓ Final SET_REPORT sent")
            except usb.core.USBError as e:
                print(f"  ⚠️  Final SET_REPORT failed: {e}")

            # Step 6: Final handshake (P#11)
            self.dev.write(ENDPOINT_BULK_OUT, handshake)
            print("  ✓ Final handshake")

            print("✅ Initialization complete!")
            return True

        except usb.core.USBError as e:
            print(f"❌ Initialization failed: {e}")
            return False

    def set_brightness(self, level: int):
        """
        Set LCD brightness (0-100)
        TODO: Need to capture brightness change packets to implement
        """
        if not 0 <= level <= 100:
            raise ValueError("Brightness must be 0-100")

        print(f"⚠️  Brightness control not yet implemented (requested: {level}%)")
        # TODO: Implement after capturing brightness packets

    def update_temperature(self, cpu_temp: float, gpu_temp: Optional[float] = None):
        """
        Update temperature display on LCD
        TODO: Need to capture temperature update packets to implement
        """
        print(f"⚠️  Temperature update not yet implemented (CPU: {cpu_temp}°C, GPU: {gpu_temp}°C)")
        # TODO: Implement after capturing temperature packets

    def close(self):
        """Clean up USB connection"""
        try:
            usb.util.dispose_resources(self.dev)
            print("✅ Device connection closed")
        except:
            pass


def main():
    """Test the driver"""
    print("=" * 60)
    print("Sama SM360 LCD AIO Driver - Test")
    print("=" * 60)

    try:
        # Connect to device
        lcd = SamaSM360()

        # Initialize
        if lcd.initialize():
            print("\n🎉 Success! Check if your LCD reacted.")
            print("\nNext steps:")
            print("1. Capture brightness change packets")
            print("2. Capture temperature update packets")
            print("3. Implement those features")
        else:
            print("\n❌ Initialization failed. Check debug output above.")

        # Clean up
        lcd.close()

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("- Is the Sama SM360 plugged in?")
        print("- Run with sudo if permission errors")
        print("- Check: lsusb | grep 1a86")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()