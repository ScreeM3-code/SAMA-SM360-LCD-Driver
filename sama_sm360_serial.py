#!/usr/bin/env python3
"""
Sama SM360 LCD Driver - Serial Protocol (COM Port)
Based on captured Windows traffic
"""

import serial
import time
import re
from typing import Optional

# Serial port configuration
BAUDRATE = 115200  # Sera confirmé
PACKET_SIZE = 250  # Taille observée dans les captures

# Theme command codes discovered
THEME_COMMANDS = {
    'STOP': 0xaa,      # Stop playback/transfer
    'SELECT': 0xbb,    # Select theme
    'TRANSFER': 0xcc,  # Transfer/Initialize transfer
    'START': 0xdd,     # Start playback
}


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

    def display_image(self, image_name: str, x: int = 0, y: int = 0):
        """
        Affiche une image (doit être présente dans le LCD)

        Args:
            image_name: Nom du fichier image
            x, y: Position
        """
        packet = bytearray(250)
        packet[0] = 0xc8
        packet[1] = 0xef
        packet[2] = 0x69
        packet[6] = 0x00  # Type = Image

        packet[7:9] = x.to_bytes(2, 'little')
        packet[9:11] = y.to_bytes(2, 'little')

        # Nom de l'image
        img_bytes = image_name.encode('utf-8')
        packet[17:17 + len(img_bytes)] = img_bytes

        self.ser.write(bytes(packet))

    def play_video(self, video_path: str = "/mnt/SDCARD/video/theme04.mp4"):
        """
        Jouer une vidéo sur le LCD

        Args:
            video_path: Chemin complet de la vidéo sur le LCD
        """
        # 1. Load video (essayer le chemin SD card en premier)
        load_packet = bytearray(250)
        load_packet[0] = 0x6e  # Load video
        load_packet[1] = 0xef
        load_packet[2] = 0x69
        load_packet[6] = 0x1d  # Subcmd pour /mnt/SDCARD

        # Chemin vidéo (UTF-8)
        path_bytes = video_path.encode('utf-8')
        load_packet[10:10 + len(path_bytes)] = path_bytes

        self.ser.write(bytes(load_packet))
        time.sleep(0.2)

        # Lire la réponse (taille du fichier ou "0" si échec)
        response = self._read_response(timeout=0.5)
        if response and response[0] != ord('0'):
            print(f"✓ Video loaded: {response.decode('utf-8').strip()[:20]} bytes")

            # 2. Play video
            play_packet = bytearray(250)
            play_packet[0] = 0x78  # Play video
            play_packet[1] = 0xef
            play_packet[2] = 0x69
            play_packet[6] = 0x1d  # Subcmd
            play_packet[7] = 0x01  # Flag "play"
            play_packet[10:10 + len(path_bytes)] = path_bytes

            self.ser.write(bytes(play_packet))
            time.sleep(0.2)

            # Lire confirmation
            response = self._read_response(timeout=0.5)
            if response and b'success' in response:
                print("✓ Video playing!")
                return True

        print("✗ Failed to load video")
        return False

    def load_and_play_video(self, video_name: str, paths: list = None) -> bool:
        """
        Load and play a video theme with full sequence
        
        Args:
            video_name: Filename (e.g., 'theme06.mp4')
            paths: List of paths to try (in order)
        
        Returns:
            True if video loaded and playing
        """
        if paths is None:
            # Try SD card first (most reliable), then /root, then /tmp
            paths = [
                f"/mnt/SDCARD/video/{video_name}",
                f"/root/video/{video_name}",
                f"/tmp/video/{video_name}"
            ]
        
        print(f"🎬 Loading video: {video_name}")
        
        for path in paths:
            print(f"  Trying: {path}")
            
            # Determine subcmd based on path
            if '/mnt/SDCARD' in path:
                subcmd = 0x1d
            elif '/root' in path:
                subcmd = 0x17
            else:  # /tmp
                subcmd = 0x16
            
            # Build load packet
            load_packet = bytearray(250)
            load_packet[0] = 0x6e  # Load video command
            load_packet[1] = 0xef
            load_packet[2] = 0x69
            load_packet[6] = subcmd
            
            path_bytes = path.encode('utf-8')
            load_packet[10:10 + len(path_bytes)] = path_bytes
            
            self.ser.write(bytes(load_packet))
            time.sleep(0.1)
            
            # Read response (should be file size or 0)
            response = self._read_response(timeout=0.3)
            if response:
                try:
                    response_text = response.decode('utf-8', errors='ignore').strip('\x00')
                    file_size = int(response_text)
                    
                    if file_size > 0:
                        print(f"    ✓ Found! Size: {file_size} bytes")
                        
                        # Send play command
                        play_packet = bytearray(250)
                        play_packet[0] = 0x78  # Play command
                        play_packet[1] = 0xef
                        play_packet[2] = 0x69
                        play_packet[6] = subcmd
                        play_packet[7] = 0x01  # Play flag
                        play_packet[10:10 + len(path_bytes)] = path_bytes
                        
                        self.ser.write(bytes(play_packet))
                        time.sleep(0.2)
                        
                        # Verify response
                        response = self._read_response(timeout=0.3)
                        if response:
                            resp_text = response.decode('utf-8', errors='ignore').strip('\x00')
                            print(f"    ✓ Play response: {resp_text[:30]}")
                        
                        print(f"✅ Video playing: {video_name}")
                        return True
                except:
                    pass
        
        print(f"❌ Video not found: {video_name}")
        return False

    def display_data(self, data_type: str, value: str, x: int, y: int,
                     font_size: int = 38, unit: str = ""):
        """
        Affiche une donnée système (CPU temp, heure, etc.)

        Args:
            data_type: Type de donnée (CPUTEMP, TIME, DATE, etc.)
            value: Valeur à afficher
            x, y: Position
            font_size: Taille police
            unit: Unité (°, RPM, etc.)
        """
        display_text = f"{value}{unit}"
        self.display_text(display_text, x, y, font_size)

    def display_text(self, text: str, x: int, y: int, font_size: int = 38,
                     color_rgb: tuple = (255, 255, 255), alignment: int = 0):
        """
        Affiche du texte à l'écran

        Args:
            text: Texte à afficher (UTF-8)
            x, y: Position en pixels
            font_size: Taille de police
            color_rgb: Couleur (R, G, B)
            alignment: 0=gauche, 1=centre, 2=droite
        """
        packet = bytearray(250)
        packet[0] = 0xc8  # Display command
        packet[1] = 0xef
        packet[2] = 0x69
        packet[6] = 0x02  # Type = Text

        # Position (little-endian, 2 bytes each)
        packet[7:9] = x.to_bytes(2, 'little')
        packet[9:11] = y.to_bytes(2, 'little')

        packet[11] = font_size

        # Couleur RGB
        r, g, b = color_rgb
        packet[12] = r
        packet[13] = g
        packet[14] = b

        packet[16] = alignment

        # Texte UTF-8
        text_bytes = text.encode('utf-8')
        packet[17:17 + len(text_bytes)] = text_bytes

        self.ser.write(bytes(packet))


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


def extract_video_path_from_config(config_file: str) -> Optional[str]:
    """
    Extract video path from theme config file (.txt)
    
    The config files contain serialized .NET objects with embedded paths.
    We look for the Linux path pattern: /mnt/SDCARD/video/...
    
    Args:
        config_file: Path to theme config file (e.g., Theme/theme06.txt)
    
    Returns:
        Video path (e.g., "/mnt/SDCARD/video/theme06.mp4") or None
    """
    try:
        with open(config_file, 'rb') as f:
            data = f.read()
        
        # Look for path patterns in the binary data
        # Pattern: /mnt/SDCARD/video/themeXX.mp4
        patterns = [
            rb'/mnt/SDCARD/video/theme\d{2}\.mp4',
            rb'/mnt/SDCARD/video/\w+\.mp4',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, data)
            if match:
                try:
                    path = match.group(0).decode('utf-8')
                    return path
                except:
                    pass
        
        # Fallback: search for any /mnt path
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
        print(f"Error reading config file {config_file}: {e}")
        return None


def list_available_themes(theme_dir: str = "Theme") -> dict:
    """
    List available theme configuration files and extract their video paths
    
    Args:
        theme_dir: Directory containing theme files
    
    Returns:
        Dictionary: {theme_name: video_path}
    """
    import os
    import glob
    
    themes = {}
    
    try:
        # Find all .txt config files
        config_files = glob.glob(os.path.join(theme_dir, "*.txt"))
        
        for config_file in sorted(config_files):
            theme_name = os.path.splitext(os.path.basename(config_file))[0]
            video_path = extract_video_path_from_config(config_file)
            
            if video_path:
                themes[theme_name] = video_path
                print(f"  ✓ {theme_name}: {video_path}")
            else:
                print(f"  ⚠ {theme_name}: (video path not found)")
        
        return themes
    
    except Exception as e:
        print(f"Error listing themes: {e}")
        return {}


def print_hex_dump(title: str, data: bytes, max_lines: int = 8):
    """Pretty print hex dump with annotations"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    
    for i in range(0, min(len(data), max_lines * 16), 16):
        chunk = data[i:i+16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        print(f"  {i:03d}: {hex_str:<48} | {ascii_str}")
    
    if len(data) > max_lines * 16:
        print(f"  ... ({len(data) - max_lines * 16} more bytes)")
    print()


def test_complete_theme_sequence(lcd, theme_name: str = "theme06"):
    """
    Test complete sequence: Init → Load Video → Play Video
    This mimics the captured log sequence
    """
    print("\n" + "="*70)
    print(f"  🎨 COMPLETE THEME SEQUENCE: {theme_name}")
    print("="*70)
    
    # Step 1: Brightness setup (observed in logs)
    print("\n[1/5] Setting brightness...")
    brightness = 128  # 50% (0x80 in captured log)
    packet = lcd._build_packet(cmd=0x7b, subcmd=0x01, value=brightness)
    print_hex_dump("0x7b - Set Brightness", packet[:30])
    lcd.ser.write(packet)
    time.sleep(0.2)
    
    response = lcd._read_response(timeout=0.2)
    if response:
        print(f"Response received: {len(response)} bytes")
    
    # Step 2: Type 5 command (observed after brightness)
    print("\n[2/5] Sending type-5 command...")
    packet = lcd._build_packet(cmd=0x7d, subcmd=0x05, value=0x80)
    print_hex_dump("0x7d - Type 5 Command", packet[:30])
    lcd.ser.write(packet)
    time.sleep(0.2)
    
    response = lcd._read_response(timeout=0.2)
    if response:
        print(f"Response received: {len(response)} bytes")
    
    # Step 3: Get status (observed before video load)
    print("\n[3/5] Getting device status...")
    status = lcd.get_status()
    if status:
        print(f"Status: {status.get('raw', status)}")
    
    # Step 4: Load and Play Video
    print("\n[4/5] Loading video theme...")
    video_loaded = lcd.load_and_play_video(f"{theme_name}.mp4")
    
    if video_loaded:
        print("\n[5/5] ✅ Theme sequence complete!")
        print(f"   {theme_name} is now playing on the LCD")
        return True
    else:
        print("\n[5/5] ⚠️  Video not found on device")
        print("   Make sure the video file is present on the SD card")
        return False


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

        # Menu for user
        print("\n" + "="*70)
        print("  SAMA SM360 LCD CONTROL MENU")
        print("="*70)
        print("\n1. Test brightness control")
        print("2. Load and play theme video (theme06)")
        print("3. Load and play custom theme")
        print("4. Test all commands")
        print("5. Get device status")
        print("6. Exit\n")
        
        choice = input("Select option (1-6): ").strip()
        
        if choice == "1":
            print("\n🔆 Testing brightness control...")
            for level in [100, 50, 100]:
                lcd.set_brightness(level)
                time.sleep(0.5)
        
        elif choice == "2":
            test_complete_theme_sequence(lcd, "theme06")
        
        elif choice == "3":
            theme = input("Enter theme name (e.g., theme04, theme17): ").strip()
            test_complete_theme_sequence(lcd, theme)
        
        elif choice == "4":
            print("\n🔆 Testing brightness control...")
            for level in [100, 50, 100]:
                lcd.set_brightness(level)
                time.sleep(0.5)
            
            print("\n🧪 Testing all commands...")
            test_display_commands(lcd)
        
        elif choice == "5":
            print("\n📊 Getting device status...")
            status = lcd.get_status()
            if status:
                print(f"Status: {status}")
        
        elif choice == "6":
            print("\nExiting...")
        
        else:
            print("Invalid choice")
        
        print("\n✅ Done!")
        lcd.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()