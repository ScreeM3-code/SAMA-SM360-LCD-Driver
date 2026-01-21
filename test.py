#!/usr/bin/env python3
"""
Sama SM360 LCD Driver - Serial Protocol (Enhanced v2)
Updated with stop/transfer/start workflow and improved file transfer handling
"""

import serial
import time
import os
import re
from typing import Optional, Union
from pathlib import Path

BAUDRATE = 115200
PACKET_SIZE = 250

# Theme command codes
THEME_COMMANDS = {
    'STOP': 0xaa,  # Stop current playback/transfer
    'SELECT': 0xbb,  # Select theme
    'TRANSFER': 0xcc,  # Transfer/Initialize transfer
    'START': 0xdd,  # Start playback
}


class SamaSM360Serial:
    def __init__(self, port='COM4'):
        """Initialize Sama SM360 via serial port"""
        self.port = 'COM4'
        self.ser = None
        self.current_theme = None

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
            self.ser.setRTS(True)
            self.ser.setDTR(True)
            time.sleep(0.1)
            print(f"✓ Connected to {self.port} at {BAUDRATE} baud")
            return True
        except serial.SerialException as e:
            print(f"✗ Failed to connect: {e}")
            return False

    def _build_packet(self, cmd: int, subcmd: int = 0x00, value: int = 0) -> bytes:
        """Build packet: [CMD] ef 69 00 00 00 [SUBCMD] [FLAGS] 00 00 [VALUE] [padding]"""
        packet = bytearray(PACKET_SIZE)
        packet[0] = cmd
        packet[1] = 0xef
        packet[2] = 0x69
        packet[3:6] = b'\x00\x00\x00'
        packet[6] = subcmd
        packet[7:10] = b'\x00\x00\x00'
        packet[10] = value & 0xFF
        return bytes(packet)

    def _read_response(self, timeout=1.0) -> Optional[bytes]:
        """Read response from LCD"""
        old_timeout = self.ser.timeout
        self.ser.timeout = timeout
        try:
            if self.ser.in_waiting > 0 or timeout > 0:
                response = self.ser.read(1024)
                if response:
                    return response
        except Exception as e:
            print(f"Read error: {e}")
        finally:
            self.ser.timeout = old_timeout
        return None

    def send_reset(self):
        """
        Send RESET command (0x2c repeated 250 times)
        Clears framebuffer and prepares for next command
        """
        reset_packet = bytes([0x2c] * PACKET_SIZE)
        self.ser.write(reset_packet)
        print("  ✓ Reset buffer (0x2c)")
        time.sleep(0.1)

    def send_post_playback(self):
        """
        Send post-playback acknowledgment (0x86)
        Sent after successful video playback
        """
        packet = self._build_packet(cmd=0x86, subcmd=0x01, value=0x00)
        self.ser.write(packet)
        print("  ✓ Post-playback ACK (0x86)")
        time.sleep(0.1)

    def stop_playback(self):
        """
        Stop current playback/transfer (0xaa)
        Required before starting new theme
        """
        packet = self._build_packet(cmd=THEME_COMMANDS['STOP'], subcmd=0x01)
        self.ser.write(packet)
        print("  ✓ Stop playback (0xaa)")
        time.sleep(0.1)

        response = self._read_response(timeout=0.3)
        if response:
            try:
                text = response.decode('utf-8', errors='ignore').strip('\x00')
                if 'stop' in text.lower():
                    print(f"    → Confirmed: {text}")
            except:
                pass

    def initialize(self) -> bool:
        """Initialize LCD with complete handshake sequence"""
        print("🔧 Initializing Sama SM360...")

        try:
            # Packet #1: Handshake (0x01)
            init_packet = self._build_packet(cmd=0x01, subcmd=0x01, value=0x00)
            init_packet = bytearray(init_packet)
            init_packet[10] = 0xc5
            init_packet[11] = 0xd3

            self.ser.write(bytes(init_packet))
            print("  ✓ Handshake sent (0x01)")
            time.sleep(0.1)

            # Read device ID
            response = self._read_response(timeout=0.5)
            if response:
                try:
                    device_id = response.decode('utf-8', errors='ignore').strip('\x00')
                    print(f"  ✓ Device: {device_id}")
                except:
                    print(f"  ✓ Device responded")

            # Secondary init (0x79)
            init2 = self._build_packet(cmd=0x79, subcmd=0x01, value=0x00)
            self.ser.write(init2)
            time.sleep(0.05)
            print("  ✓ Init phase 2 (0x79)")

            # Tertiary init (0x96)
            init3 = self._build_packet(cmd=0x96, subcmd=0x01, value=0x00)
            self.ser.write(init3)
            time.sleep(0.05)

            # Check for "media_stop" response
            response = self._read_response(timeout=0.3)
            if response and b'media_stop' in response:
                print("  ✓ Init phase 3 (0x96) → media_stop")
            else:
                print("  ✓ Init phase 3 (0x96)")

            print("✅ Initialization complete!")
            return True

        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False

    def transfer_file(self, file_path: str, destination: str = "/mnt/SDCARD/video/") -> bool:
        """
        Transfer file to LCD (if file transfer is supported)
        Based on USB sniffing, files may need to be transferred

        Args:
            file_path: Local file path (e.g., "theme_custom.mp4")
            destination: Destination path on LCD
        """
        if not os.path.exists(file_path):
            print(f"✗ File not found: {file_path}")
            return False

        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)

        print(f"📤 Transferring {file_name} ({file_size} bytes)...")

        # Use TRANSFER command (0xcc)
        transfer_packet = self._build_packet(cmd=THEME_COMMANDS['TRANSFER'], subcmd=0x1d)
        transfer_packet = bytearray(transfer_packet)

        # Add destination path
        dest_path = destination + file_name
        path_bytes = dest_path.encode('utf-8')
        transfer_packet[10:10 + len(path_bytes)] = path_bytes

        self.ser.write(bytes(transfer_packet))
        time.sleep(0.2)

        # Read ACK
        response = self._read_response(timeout=0.5)
        if response and b'ready' in response.lower():
            print("  ✓ Transfer ready")

            # Send file data in chunks
            with open(file_path, 'rb') as f:
                chunk_size = PACKET_SIZE - 20  # Reserve space for headers
                bytes_sent = 0

                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break

                    # Build data packet
                    data_packet = bytearray(PACKET_SIZE)
                    data_packet[0] = 0xcc  # Transfer command
                    data_packet[1] = 0xef
                    data_packet[2] = 0x69
                    data_packet[10:10 + len(chunk)] = chunk

                    self.ser.write(bytes(data_packet))
                    bytes_sent += len(chunk)

                    if bytes_sent % 10240 == 0:  # Progress every 10KB
                        print(f"  → {bytes_sent}/{file_size} bytes ({bytes_sent * 100 // file_size}%)")

                    time.sleep(0.01)  # Small delay between packets

                print(f"  ✓ Transfer complete: {bytes_sent} bytes")
                return True

        print("  ✗ Transfer failed")
        return False

    def load_and_play_video(self, video_name: str, paths: list = None,
                            auto_stop: bool = True) -> bool:
        """
        Complete workflow: Stop → Load → Play → Post-playback → Reset

        Args:
            video_name: Filename (e.g., 'theme10.mp4')
            paths: List of paths to try
            auto_stop: Automatically stop current playback first
        """
        if paths is None:
            paths = [
                f"/mnt/SDCARD/video/{video_name}",
                f"/root/video/{video_name}",
                f"/tmp/video/{video_name}"
            ]

        print(f"\n🎬 Loading theme: {video_name}")

        # STEP 0: Stop current playback (if requested)
        if auto_stop:
            print("\n[1/5] Stopping current playback...")
            self.stop_playback()

        step_offset = 1 if auto_stop else 0

        for path in paths:
            print(f"\n[{2 + step_offset}/5] Trying: {path}")

            # Determine subcmd based on path
            if '/mnt/SDCARD' in path:
                subcmd = 0x1d
            elif '/root' in path:
                subcmd = 0x17
            else:  # /tmp
                subcmd = 0x16

            # STEP 1: Load video (0x6e)
            load_packet = bytearray(PACKET_SIZE)
            load_packet[0] = 0x6e
            load_packet[1] = 0xef
            load_packet[2] = 0x69
            load_packet[6] = subcmd

            path_bytes = path.encode('utf-8')
            load_packet[10:10 + len(path_bytes)] = path_bytes

            self.ser.write(bytes(load_packet))
            time.sleep(0.1)

            # Read file size
            response = self._read_response(timeout=0.3)
            if response:
                try:
                    response_text = response.decode('utf-8', errors='ignore').strip('\x00')
                    file_size = int(response_text)

                    if file_size > 0:
                        print(f"  ✓ Found! Size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")

                        # STEP 2: Play video (0x78)
                        print(f"\n[{3 + step_offset}/5] Playing video...")
                        play_packet = bytearray(PACKET_SIZE)
                        play_packet[0] = 0x78
                        play_packet[1] = 0xef
                        play_packet[2] = 0x69
                        play_packet[6] = subcmd
                        play_packet[7] = 0x01  # Play flag
                        play_packet[10:10 + len(path_bytes)] = path_bytes

                        self.ser.write(bytes(play_packet))
                        time.sleep(0.2)

                        # Verify playback started
                        response = self._read_response(timeout=0.3)
                        if response and b'success' in response:
                            print(f"  ✓ Playback started")

                            # STEP 3: Post-playback ACK (0x86)
                            print(f"\n[{4 + step_offset}/5] Sending acknowledgment...")
                            self.send_post_playback()

                            # STEP 4: Reset buffer (0x2c)
                            print(f"\n[{5 + step_offset}/5] Resetting buffer...")
                            self.send_reset()

                            self.current_theme = video_name
                            print(f"\n✅ Theme active: {video_name}")
                            return True
                except:
                    pass

        print(f"\n❌ Video not found: {video_name}")
        return False

    def set_brightness(self, brightness: int) -> bool:
        """Set LCD brightness (0-100)"""
        if not 0 <= brightness <= 100:
            raise ValueError("Brightness must be 0-100")

        value = int((brightness / 100.0) * 255)

        try:
            packet = self._build_packet(cmd=0x7b, subcmd=0x01, value=value)
            self.ser.write(packet)
            print(f"  ✓ Brightness: {brightness}% (0x{value:02x})")

            response = self._read_response(timeout=0.2)
            return True
        except Exception as e:
            print(f"  ✗ Failed to set brightness: {e}")
            return False

    def get_status(self) -> Optional[dict]:
        """Get device monitoring status"""
        try:
            status_req = self._build_packet(cmd=0x64, subcmd=0x01, value=0x00)
            self.ser.write(status_req)

            response = self._read_response(timeout=0.5)
            if response:
                try:
                    text = response.decode('utf-8', errors='ignore').strip('\x00')
                    if '-' in text:
                        values = text.split('-')
                        return {
                            'raw': text,
                            'values': [int(v) for v in values if v.isdigit()],
                            'cpu_fan_rpm': int(values[0]) if len(values) > 0 else None,
                            'gpu_fan_rpm': int(values[1]) if len(values) > 1 else None,
                            'cpu_temp': int(values[2]) / 100 if len(values) > 2 else None,  # Divided by 100
                        }
                except:
                    pass
                return {'raw_hex': response.hex()}
            return None
        except Exception as e:
            print(f"Error getting status: {e}")
            return None

    def display_text(self, text: str, x: int, y: int, font_size: int = 38,
                     color_rgb: tuple = (255, 255, 255), alignment: int = 0):
        """
        Display text on screen (0xc8 command)
        Structure based on captures - may need refinement
        """
        packet = bytearray(PACKET_SIZE)
        packet[0] = 0xc8  # Display command
        packet[1] = 0xef
        packet[2] = 0x69
        packet[6] = 0x02  # Subcmd: Text type

        # Position (little-endian, 2 bytes each)
        packet[7:9] = x.to_bytes(2, 'little')
        packet[9:11] = y.to_bytes(2, 'little')

        packet[11] = font_size

        # RGB color
        r, g, b = color_rgb
        packet[12] = r
        packet[13] = g
        packet[14] = b

        packet[16] = alignment  # 0=left, 1=center, 2=right

        # UTF-8 text
        text_bytes = text.encode('utf-8')
        packet[17:17 + len(text_bytes)] = text_bytes

        self.ser.write(bytes(packet))
        time.sleep(0.05)

    def display_image(self, image_path: str, x: int = 0, y: int = 0):
        """
        Display static image (must be present on LCD)

        Args:
            image_path: Path on LCD (e.g., "/mnt/SDCARD/images/logo.png")
            x, y: Position
        """
        packet = bytearray(PACKET_SIZE)
        packet[0] = 0xc8
        packet[1] = 0xef
        packet[2] = 0x69
        packet[6] = 0x00  # Subcmd: Image type

        packet[7:9] = x.to_bytes(2, 'little')
        packet[9:11] = y.to_bytes(2, 'little')

        # Image path
        img_bytes = image_path.encode('utf-8')
        packet[17:17 + len(img_bytes)] = img_bytes

        self.ser.write(bytes(packet))
        time.sleep(0.05)

    def close(self):
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("✅ Port closed")


def extract_video_path_from_config(config_file: str) -> Optional[str]:
    """Extract video path from theme config file (.txt)"""
    try:
        with open(config_file, 'rb') as f:
            data = f.read()

        # Look for /mnt/SDCARD/video/themeXX.mp4 pattern
        patterns = [
            rb'/mnt/SDCARD/video/theme\d{2}\.mp4',
            rb'/mnt/SDCARD/video/\w+\.mp4',
        ]

        for pattern in patterns:
            match = re.search(pattern, data)
            if match:
                try:
                    return match.group(0).decode('utf-8')
                except:
                    pass

        # Fallback: any .mp4 path
        match = re.search(rb'/mnt/[^"\x00]+\.mp4', data)
        if match:
            try:
                path = match.group(0).decode('utf-8', errors='ignore').strip('\x00')
                if '.mp4' in path:
                    return path
            except:
                pass

        return None
    except Exception as e:
        print(f"Error reading {config_file}: {e}")
        return None


def list_available_themes(theme_dir: str = "Theme") -> dict:
    """List available theme configurations"""
    import glob

    themes = {}

    try:
        config_files = glob.glob(os.path.join(theme_dir, "*.txt"))

        for config_file in sorted(config_files):
            theme_name = os.path.splitext(os.path.basename(config_file))[0]
            video_path = extract_video_path_from_config(config_file)

            if video_path:
                themes[theme_name] = video_path
                print(f"  ✓ {theme_name}: {os.path.basename(video_path)}")
            else:
                print(f"  ⚠ {theme_name}: (video path not found)")

        return themes
    except Exception as e:
        print(f"Error listing themes: {e}")
        return {}


def main():
    """Enhanced interactive menu"""
    print("=" * 70)
    print("Sama SM360 LCD Driver - Enhanced v2.0")
    print("Stop → Transfer → Start Workflow")
    print("=" * 70)

    # Auto-detect COM port
    import serial.tools.list_ports

    ports = list(serial.tools.list_ports.comports())
    sama_port = None

    print("\nDetecting COM ports:")
    for port in ports:
        print(f"  {port.device}: {port.description}")
        if '1A86' in port.hwid or 'CA21' in port.hwid:
            sama_port = port.device
            print(f"    ✓ Sama SM360 detected!")

    if not sama_port:
        sama_port = input("\nEnter COM port (default: COM4): ").strip() or 'COM4'

    try:
        lcd = SamaSM360Serial(sama_port)

        if not lcd.connect():
            return

        if not lcd.initialize():
            return

        while True:
            print("\n" + "=" * 70)
            print("  SAMA SM360 CONTROL MENU")
            print("=" * 70)
            print("\n1. Load and play theme (with auto-stop)")
            print("2. Stop current playback")
            print("3. Set brightness")
            print("4. Get device status")
            print("5. Display custom text")
            print("6. List available themes")
            print("7. Reset buffer (0x2c)")
            print("0. Exit\n")

            choice = input("Select option: ").strip()

            if choice == "1":
                theme = input("Enter theme name (e.g., theme10): ").strip()
                if not theme.endswith('.mp4'):
                    theme += '.mp4'
                lcd.load_and_play_video(theme, auto_stop=True)

            elif choice == "2":
                lcd.stop_playback()

            elif choice == "3":
                level = int(input("Enter brightness (0-100): ").strip())
                lcd.set_brightness(level)

            elif choice == "4":
                print("\n📊 Device Status:")
                status = lcd.get_status()
                if status:
                    print(f"  Raw: {status.get('raw', 'N/A')}")
                    if 'cpu_fan_rpm' in status:
                        print(f"  CPU Fan: {status['cpu_fan_rpm']} RPM")
                        print(f"  GPU Fan: {status['gpu_fan_rpm']} RPM")
                        print(f"  CPU Temp: {status['cpu_temp']:.2f}°C")

            elif choice == "5":
                text = input("Enter text: ").strip()
                x = int(input("X position (default: 100): ").strip() or "100")
                y = int(input("Y position (default: 100): ").strip() or "100")
                lcd.display_text(text, x, y)

            elif choice == "6":
                print("\n📁 Available Themes:")
                themes = list_available_themes()
                if themes:
                    print(f"\nFound {len(themes)} theme(s)")

            elif choice == "7":
                lcd.send_reset()

            elif choice == "0":
                print("\n👋 Exiting...")
                break

            else:
                print("Invalid choice")

        lcd.close()

    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()