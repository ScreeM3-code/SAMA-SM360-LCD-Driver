#!/usr/bin/env python3
"""
SAMA SM360 LCD Driver - PNG Display System
Based on .turtheme file analysis

BREAKTHROUGH DISCOVERY:
- LCD displays PNG images, not raw pixels!
- Theme files (.turtheme) are .NET serialized objects containing PNG data
- Workflow: STOP → INIT → SEND PNG → Display

The "pixel data" we saw was actually PNG file data!
"""

import serial
import time
from typing import Tuple, Optional
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    print("⚠ PIL not installed. Install with: pip install Pillow")
    Image = None


class SamaPNGDisplay:
    """Driver for SAMA SM360 PNG display system"""

    # Display specifications from .turtheme analysis
    DISPLAY_WIDTH = 480
    DISPLAY_HEIGHT = 480

    # Commands
    CMD_STOP = 0xaa
    CMD_INIT_1 = 0x01
    CMD_INIT_2 = 0x79
    CMD_INIT_3 = 0x96
    CMD_SEND_PNG = 0x87  # Actually sends PNG data!
    CMD_MAGIC_HEADER = bytes([0xef, 0x69])

    def __init__(self, port='COM4', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self):
        """Open serial connection"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=2
            )
            print(f"✓ Connected to {self.port}")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    def _wait_for_response(self, expected: str = None, timeout: float = 2.0) -> Optional[str]:
        """Wait for LCD response"""
        if expected:
            print(f"⏳ Waiting for: {expected}")

        start_time = time.time()
        buffer = b''

        while time.time() - start_time < timeout:
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting)
                buffer += data

                try:
                    text = buffer.decode('utf-8', errors='ignore').strip('\x00')

                    if text and (not expected or expected in text):
                        print(f"✓ Response: {text[:60]}")
                        return text

                except:
                    pass

            time.sleep(0.01)

        return None

    def stop_current_display(self) -> bool:
        """STOP current display"""
        print("\n⏹️  STOPPING current display...")

        packet = bytearray(250)
        packet[0] = self.CMD_STOP
        packet[1:3] = self.CMD_MAGIC_HEADER
        packet[6] = 0x01

        self.ser.write(bytes(packet))
        time.sleep(0.2)

        print("✓ Stop command sent")
        return True

    def initialize(self) -> bool:
        """Initialize LCD"""
        print("\n🔧 INITIALIZING LCD...")

        # 1. Handshake with special bytes
        packet1 = bytearray(250)
        packet1[0] = self.CMD_INIT_1
        packet1[1:3] = self.CMD_MAGIC_HEADER
        packet1[6] = 0x01
        packet1[10] = 0xc5
        packet1[11] = 0xd3
        self.ser.write(bytes(packet1))
        time.sleep(0.1)

        self._wait_for_response("chs_5inch", timeout=1.0)

        # 2. Secondary init
        packet2 = bytearray(250)
        packet2[0] = self.CMD_INIT_2
        packet2[1:3] = self.CMD_MAGIC_HEADER
        packet2[6] = 0x01
        self.ser.write(bytes(packet2))
        time.sleep(0.1)

        # 3. Tertiary init
        packet3 = bytearray(250)
        packet3[0] = self.CMD_INIT_3
        packet3[1:3] = self.CMD_MAGIC_HEADER
        packet3[6] = 0x01
        self.ser.write(bytes(packet3))
        time.sleep(0.1)

        self._wait_for_response("media_stop", timeout=1.0)

        print("✅ LCD initialized\n")
        return True

    def create_solid_color_png(self, r: int, g: int, b: int) -> bytes:
        """
        Create a PNG image with solid color

        Args:
            r, g, b: RGB color (0-255)

        Returns:
            PNG file data as bytes
        """
        if not Image:
            raise RuntimeError("PIL/Pillow is required. Install with: pip install Pillow")

        print(f"🎨 Creating {self.DISPLAY_WIDTH}x{self.DISPLAY_HEIGHT} PNG with RGB({r},{g},{b})...")

        # Create image
        img = Image.new('RGB', (self.DISPLAY_WIDTH, self.DISPLAY_HEIGHT), (r, g, b))

        # Save to bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG', optimize=False)
        png_data = buffer.getvalue()

        print(f"✓ PNG created ({len(png_data)} bytes)")

        return png_data

    def send_png_data(self, png_data: bytes) -> bool:
        """
        Send PNG data to LCD

        This is what command 0x87 actually does - it receives PNG data!
        """
        print(f"\n📤 SENDING PNG DATA ({len(png_data)} bytes)...")

        # Step 1: Send preparation command (0x87)
        print("  Step 1: Sending preparation command (0x87)...")
        prep_packet = bytearray(250)
        prep_packet[0] = self.CMD_SEND_PNG
        prep_packet[1:3] = self.CMD_MAGIC_HEADER
        prep_packet[6] = 0x01
        self.ser.write(bytes(prep_packet))
        time.sleep(0.2)

        # Step 2: Send PNG data in chunks
        print("  Step 2: Sending PNG data...")
        chunk_size = 1024
        total_chunks = (len(png_data) + chunk_size - 1) // chunk_size

        for i in range(0, len(png_data), chunk_size):
            chunk = png_data[i:i + chunk_size]
            chunk_num = i // chunk_size + 1

            self.ser.write(chunk)
            print(f"    Chunk {chunk_num}/{total_chunks} sent", end='\r')
            time.sleep(0.01)

        print(f"\n  ✓ All {total_chunks} chunks sent")

        # Step 3: Wait for confirmation
        print("  Step 3: Waiting for confirmation...")
        response = self._wait_for_response("full_png_sucess", timeout=5.0)

        if response:
            print("  ✓ LCD confirmed PNG received!")

            # Also check for render count
            render_response = self._wait_for_response("renderCnt", timeout=2.0)
            if render_response:
                print("  ✓ PNG rendered on display!")

            return True
        else:
            print("  ✗ No confirmation received")
            return False

    def display_solid_color(self, r: int, g: int, b: int) -> bool:
        """
        Complete workflow to display solid color

        WORKFLOW:
        1. STOP current display
        2. INIT LCD
        3. CREATE PNG with color
        4. SEND PNG to LCD

        Args:
            r, g, b: RGB color (0-255)
        """
        print(f"\n{'=' * 70}")
        print(f"🎨 DISPLAYING SOLID COLOR: RGB({r}, {g}, {b})")
        print(f"{'=' * 70}")

        # STEP 1: Stop current display
        if not self.stop_current_display():
            return False

        # STEP 2: Initialize
        if not self.initialize():
            return False

        # STEP 3: Create PNG
        try:
            png_data = self.create_solid_color_png(r, g, b)
        except Exception as e:
            print(f"✗ PNG creation failed: {e}")
            return False

        # STEP 4: Send PNG
        if not self.send_png_data(png_data):
            return False

        print(f"\n{'=' * 70}")
        print("✅ COLOR DISPLAYED SUCCESSFULLY!")
        print(f"{'=' * 70}\n")

        return True

    def display_png_file(self, png_path: str) -> bool:
        """
        Display a PNG file from disk

        Args:
            png_path: Path to PNG file
        """
        print(f"\n{'=' * 70}")
        print(f"📁 LOADING PNG: {png_path}")
        print(f"{'=' * 70}")

        try:
            with open(png_path, 'rb') as f:
                png_data = f.read()

            print(f"✓ PNG loaded ({len(png_data)} bytes)")

            # Verify it's a valid PNG
            if not png_data.startswith(b'\x89PNG'):
                print("✗ Invalid PNG file!")
                return False

            # Stop and init
            if not self.stop_current_display():
                return False

            if not self.initialize():
                return False

            # Send PNG
            return self.send_png_data(png_data)

        except Exception as e:
            print(f"✗ Error: {e}")
            return False

    def close(self):
        """Close connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("✓ Connection closed")


def demo_colors():
    """Demo showing color changes"""
    lcd = SamaPNGDisplay('COM4')

    if not lcd.connect():
        return

    try:
        print("""
╔═══════════════════════════════════════════════════════════════╗
║         SAMA SM360 - PNG Display System                      ║
║                                                               ║
║  BREAKTHROUGH: LCD displays PNG images!                       ║
║                                                               ║
║  - Creates 480x480 PNG with solid color                      ║
║  - Sends PNG data via command 0x87                           ║
║  - LCD responds with "full_png_sucess"                       ║
║  - Display updates!                                          ║
╚═══════════════════════════════════════════════════════════════╝
        """)

        if not Image:
            print("\n❌ Pillow library required!")
            print("Install with: pip install Pillow")
            return

        # Test sequence: Blue → Red → Green
        colors = [
            (0, 0, 255, "Blue"),
            (255, 0, 0, "Red"),
            (0, 255, 0, "Green"),
        ]

        for r, g, b, name in colors:
            print(f"\n{'=' * 70}")
            print(f"Next color: {name}")
            print(f"{'=' * 70}")

            input("Press ENTER to continue...")

            success = lcd.display_solid_color(r, g, b)

            if not success:
                print(f"⚠ Failed to display {name}")
                break

            time.sleep(2)

        print("\n✅ Demo complete!")

    finally:
        lcd.close()


def demo_custom_png():
    """Demo showing custom PNG file"""
    lcd = SamaPNGDisplay('COM4')

    if not lcd.connect():
        return

    try:
        png_path = input("Enter path to PNG file (480x480 recommended): ")

        if not png_path:
            print("No file specified")
            return

        lcd.display_png_file(png_path)

    finally:
        lcd.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--file":
        demo_custom_png()
    else:
        demo_colors()