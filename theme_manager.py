#!/usr/bin/env python3
"""
SAMA SM360 LCD - Theme Manager
Handles theme selection, transfer, and playback with START/STOP control
Supports multiple resolutions (240x320, 320x320, 480x480, 720x720, 800x1280)
"""

import os
import sys
import time
from pathlib import Path
from sama_sm360_serial import SamaSM360Serial, print_hex_dump


class ThemeManager:
    """Manages theme selection and video playback on SAMA SM360 LCD"""
    
    # Resolution folders mapping
    RESOLUTIONS = {
        '240x320 (Portrait)': '240320',
        '320x320 (Square)': '320320',
        '480x480 (Rotate)': '480480r',
        '480x480 (Square)': '480480s',
        '720x720': '720720',
        '800x1280': '8001280',
    }
    
    def __init__(self, serial_port='COM4', resolution='480480r'):
        """
        Initialize Theme Manager
        
        Args:
            serial_port: COM port (default: COM4)
            resolution: Resolution folder (default: 480480r for 480x480 rotate)
        """
        self.serial_port = serial_port
        self.resolution = resolution
        self.lcd = None
        
        # Base directories
        self.video_dir = 'Video sama'
        self.theme_dir = 'Theme Sama'
        self.restor_dir = 'Restor Sama'
        
        # Resolution-specific paths
        self.video_path = os.path.join(self.video_dir, resolution)
        self.theme_path = os.path.join(self.theme_dir, resolution)
        self.restor_path = os.path.join(self.restor_dir, resolution)
        self.fonts_path = os.path.join(self.theme_dir, 'fonts')
        
        # Verify paths exist
        self._verify_paths()
    
    def _verify_paths(self):
        """Verify all required directories exist"""
        paths = {
            'Videos': self.video_path,
            'Themes': self.theme_path,
            'Resources': self.restor_path,
            'Fonts': self.fonts_path,
        }
        
        print("\n📁 Verifying directory structure...")
        for name, path in paths.items():
            if os.path.isdir(path):
                print(f"  ✓ {name}: {path}")
            else:
                print(f"  ❌ {name} NOT FOUND: {path}")
                if name != 'Fonts':  # Fonts are optional
                    raise FileNotFoundError(f"Required directory missing: {path}")
    
    def list_available_themes(self):
        """
        List all available themes for current resolution
        Returns a dictionary mapping theme name to video path
        """
        themes = {}
        
        try:
            video_files = os.listdir(self.video_path)
            
            for video_file in sorted(video_files):
                if video_file.endswith('.mp4'):
                    # Extract theme name from video filename (remove .mp4)
                    theme_name = video_file[:-4]  # Remove .mp4
                    video_full_path = os.path.join(self.video_path, video_file)
                    
                    # Check if corresponding theme config exists
                    config_file = os.path.join(self.theme_path, f"{theme_name}.turtheme")
                    
                    themes[theme_name] = {
                        'video': video_full_path,
                        'video_file': video_file,
                        'config': config_file if os.path.exists(config_file) else None,
                    }
            
            return themes
        except FileNotFoundError:
            print(f"❌ Video directory not found: {self.video_path}")
            return {}
    
    def get_restor_files(self, theme_name: str):
        """
        Get resource files (.turtheme) for a theme
        
        Args:
            theme_name: Theme name (e.g., "theme04")
            
        Returns:
            List of resource file paths
        """
        restor_files = []
        
        try:
            # Look for .turtheme files matching the theme name
            for file in os.listdir(self.restor_path):
                if file.startswith(theme_name) and file.endswith('.turtheme'):
                    restor_files.append(os.path.join(self.restor_path, file))
        except FileNotFoundError:
            pass
        
        return restor_files
    
    def get_fonts(self):
        """
        Get available fonts
        
        Returns:
            List of font file paths
        """
        fonts = []
        
        try:
            for file in os.listdir(self.fonts_path):
                if file.endswith(('.ttf', '.otf')):
                    fonts.append(os.path.join(self.fonts_path, file))
        except FileNotFoundError:
            pass
        
        return sorted(fonts)
    
    def print_theme_info(self, theme_name: str, theme_info: dict):
        """Pretty print theme information"""
        print(f"\n{'='*70}")
        print(f"  🎨 THEME: {theme_name}")
        print(f"{'='*70}")
        print(f"  📹 Video:     {theme_info['video']}")
        print(f"  📄 Config:    {theme_info['config'] if theme_info['config'] else '(not found)'}")
        
        # Get resources
        restor_files = self.get_restor_files(theme_name)
        if restor_files:
            print(f"  📦 Resources: {len(restor_files)} file(s)")
            for rf in restor_files:
                print(f"       - {os.path.basename(rf)}")
        
        print(f"{'='*70}\n")
    
    def connect(self):
        """Connect to LCD"""
        self.lcd = SamaSM360Serial(self.serial_port)
        self.lcd.connect()
        return self.lcd
    
    def stop_playback(self):
        """Stop current video playback"""
        if not self.lcd:
            return False
        
        print("\n⏹️  STOPPING current playback...")
        
        # STOP command (tentative: 0xaa)
        stop_packet = bytearray(250)
        stop_packet[0] = 0xaa  # STOP command
        stop_packet[1] = 0xef
        stop_packet[2] = 0x69
        stop_packet[6] = 0x01
        
        print_hex_dump("STOP packet (0xaa)", bytes(stop_packet[:30]))
        
        self.lcd.ser.write(bytes(stop_packet))
        time.sleep(0.2)
        
        response = self.lcd._read_response(timeout=0.3)
        if response:
            resp_text = response.decode('utf-8', errors='ignore').strip('\x00')
            print(f"  Response: {resp_text[:50]}")
        
        print("  ✓ Stop command sent")
        return True
    
    def select_theme(self, theme_name: str):
        """Select a theme (prepare for transfer)"""
        if not self.lcd:
            return False
        
        print(f"\n📁 SELECTING theme: {theme_name}...")
        
        # SELECT command (tentative: 0xbb)
        select_packet = bytearray(250)
        select_packet[0] = 0xbb  # SELECT command
        select_packet[1] = 0xef
        select_packet[2] = 0x69
        select_packet[6] = 0x01
        
        # Add theme name as data
        theme_bytes = theme_name.encode('utf-8')[:30]
        select_packet[10:10+len(theme_bytes)] = theme_bytes
        
        print_hex_dump(f"SELECT packet (0xbb) - {theme_name}", bytes(select_packet[:40]))
        
        self.lcd.ser.write(bytes(select_packet))
        time.sleep(0.2)
        
        response = self.lcd._read_response(timeout=0.3)
        if response:
            resp_text = response.decode('utf-8', errors='ignore').strip('\x00')
            print(f"  Response: {resp_text[:50]}")
        
        print(f"  ✓ Theme selected: {theme_name}")
        return True
    
    def transfer_theme(self, video_path: str):
        """Transfer video/theme to device"""
        if not self.lcd:
            return False
        
        print(f"\n📤 TRANSFERRING video to device...")
        print(f"   Path: {video_path}")
        
        # TRANSFER command (tentative: 0xcc)
        transfer_packet = bytearray(250)
        transfer_packet[0] = 0xcc  # TRANSFER command
        transfer_packet[1] = 0xef
        transfer_packet[2] = 0x69
        transfer_packet[6] = 0x1d  # /mnt/SDCARD path selector
        
        # Add video path as data
        path_bytes = video_path.encode('utf-8')[:230]
        transfer_packet[10:10+len(path_bytes)] = path_bytes
        
        print_hex_dump("TRANSFER packet (0xcc)", bytes(transfer_packet[:50]))
        
        self.lcd.ser.write(bytes(transfer_packet))
        time.sleep(0.5)
        
        response = self.lcd._read_response(timeout=1.0)
        if response:
            resp_text = response.decode('utf-8', errors='ignore').strip('\x00')
            print(f"  Response: {resp_text[:50]}")
        
        print("  ✓ Transfer initiated")
        return True
    
    def start_playback(self):
        """Start video playback"""
        if not self.lcd:
            return False
        
        print(f"\n▶️  STARTING playback...")
        
        # START command (tentative: 0xdd)
        start_packet = bytearray(250)
        start_packet[0] = 0xdd  # START command
        start_packet[1] = 0xef
        start_packet[2] = 0x69
        start_packet[6] = 0x01
        start_packet[10] = 0x01  # Play flag
        
        print_hex_dump("START packet (0xdd)", bytes(start_packet[:30]))
        
        self.lcd.ser.write(bytes(start_packet))
        time.sleep(0.2)
        
        response = self.lcd._read_response(timeout=0.3)
        if response:
            resp_text = response.decode('utf-8', errors='ignore').strip('\x00')
            print(f"  Response: {resp_text[:50]}")
        
        print("  ✓ Playback started")
        return True
    
    def change_theme_complete(self, theme_name: str):
        """
        Complete theme change sequence
        STOP → SELECT → TRANSFER → START
        """
        if not self.lcd:
            return False
        
        # Get theme info
        themes = self.list_available_themes()
        if theme_name not in themes:
            print(f"\n❌ Theme not found: {theme_name}")
            return False
        
        theme_info = themes[theme_name]
        self.print_theme_info(theme_name, theme_info)
        
        print(f"{'='*70}")
        print(f"  🎬 CHANGING THEME: {theme_name}")
        print(f"{'='*70}\n")
        
        # Execute sequence
        if not self.stop_playback():
            return False
        time.sleep(0.3)
        
        if not self.select_theme(theme_name):
            return False
        time.sleep(0.3)
        
        # Use /mnt/SDCARD path (on device storage)
        device_video_path = f"/mnt/SDCARD/video/{theme_info['video_file']}"
        if not self.transfer_theme(device_video_path):
            return False
        time.sleep(0.3)
        
        if not self.start_playback():
            return False
        
        print(f"\n✅ Theme change complete: {theme_name} is now playing!\n")
        return True
    
    def interactive_menu(self):
        """Interactive menu for theme management"""
        while True:
            print("\n" + "="*70)
            print("  📺 SAMA SM360 LCD - Theme Manager")
            print("="*70)
            print(f"  Current Resolution: {self.resolution}")
            print(f"  Serial Port: {self.serial_port}")
            print("="*70)
            print("\n  1. List available themes")
            print("  2. Change theme (interactive)")
            print("  3. Change theme (direct name)")
            print("  4. Stop playback")
            print("  5. Get device status")
            print("  6. Disconnect and exit")
            print("\n" + "="*70)
            
            choice = input("\n  Select option: ").strip()
            
            if choice == '1':
                # List themes
                themes = self.list_available_themes()
                if themes:
                    print(f"\n  📁 Available themes ({len(themes)} found):")
                    for theme_name in themes:
                        print(f"    ✓ {theme_name}")
                else:
                    print("  ❌ No themes found")
            
            elif choice == '2':
                # Interactive theme selection
                themes = self.list_available_themes()
                if not themes:
                    print("  ❌ No themes found")
                    continue
                
                print(f"\n  📁 Available themes:")
                theme_list = list(themes.keys())
                for i, theme in enumerate(theme_list, 1):
                    print(f"    {i}. {theme}")
                
                try:
                    theme_num = int(input("\n  Select theme number: ")) - 1
                    if 0 <= theme_num < len(theme_list):
                        selected_theme = theme_list[theme_num]
                        if self.change_theme_complete(selected_theme):
                            input("\n  Press Enter to continue...")
                    else:
                        print("  ❌ Invalid selection")
                except ValueError:
                    print("  ❌ Invalid input")
            
            elif choice == '3':
                # Direct theme name
                theme_name = input("\n  Enter theme name: ").strip()
                if theme_name:
                    if self.change_theme_complete(theme_name):
                        input("\n  Press Enter to continue...")
            
            elif choice == '4':
                # Stop playback
                if self.lcd:
                    self.stop_playback()
                    input("\n  Press Enter to continue...")
                else:
                    print("  ❌ LCD not connected")
            
            elif choice == '5':
                # Get status
                if self.lcd:
                    status = self.lcd.get_status()
                    if status:
                        print(f"\n  📊 Device Status: {status['raw']}")
                    else:
                        print("  ❌ Could not get status")
                    input("\n  Press Enter to continue...")
                else:
                    print("  ❌ LCD not connected")
            
            elif choice == '6':
                # Exit
                if self.lcd:
                    self.lcd.close()
                print("\n  👋 Goodbye!\n")
                break
            
            else:
                print("  ❌ Invalid option")


def main():
    """Main entry point"""
    try:
        # Initialize theme manager
        print("\n" + "="*70)
        print("  🚀 SAMA SM360 LCD - Theme Manager")
        print("="*70)
        
        # Get serial port
        serial_port = input("\n  Enter serial port (default: COM4): ").strip() or 'COM4'
        
        # Display available resolutions
        print("\n  Available resolutions:")
        resolution_list = list(ThemeManager.RESOLUTIONS.items())
        for i, (name, folder) in enumerate(resolution_list, 1):
            print(f"    {i}. {name} ({folder})")
        
        try:
            res_num = int(input("\n  Select resolution (default: 4): ").strip() or '4') - 1
            if 0 <= res_num < len(resolution_list):
                resolution = resolution_list[res_num][1]
            else:
                resolution = '480480r'  # Default
        except ValueError:
            resolution = '480480r'
        
        # Create theme manager
        manager = ThemeManager(serial_port=serial_port, resolution=resolution)
        
        # Connect to LCD
        print("\n  🔌 Connecting to LCD...")
        manager.connect()
        
        # Initialize LCD
        print("  ⚙️  Initializing LCD...")
        manager.lcd.initialize()
        
        # Start interactive menu
        manager.interactive_menu()
        
    except KeyboardInterrupt:
        print("\n\n  ⏸️  Interrupted by user")
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
