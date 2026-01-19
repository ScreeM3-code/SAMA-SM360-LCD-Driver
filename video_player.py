#!/usr/bin/env python3
"""
SAMA SM360 LCD - Video Player
Correct implementation based on captured log analysis
Sequence: STOP → LOAD VIDEO (test all paths) → POLL STATUS → PLAY
"""

import os
import sys
import time
from pathlib import Path
from sama_sm360_serial import SamaSM360Serial, print_hex_dump


class VideoPlayer:
    """Controls video playback on SAMA SM360 LCD"""
    
    # Video paths to test (in order of priority)
    VIDEO_PATHS = {
        '/tmp/video': 0x16,          # Temporary
        '/root/video': 0x17,         # Home directory
        '/mnt/SDCARD/video': 0x1d,   # SD card (most likely)
    }
    
    # Resolution folders
    RESOLUTIONS = {
        '240x320 (Portrait)': '240320',
        '320x320 (Square)': '320320',
        '480x480 (Rotate)': '480480r',
        '480x480 (Square)': '480480s',
        '720x720': '720720',
        '800x1280': '8001280',
    }
    
    def __init__(self, serial_port='COM4', resolution='480480r'):
        """Initialize Video Player"""
        self.serial_port = serial_port
        self.resolution = resolution
        self.lcd = None
        
        # Base directories
        self.video_dir = 'Video sama'
        self.theme_dir = 'Theme Sama'
        
        # Resolution-specific paths
        self.video_path = os.path.join(self.video_dir, resolution)
        self.theme_path = os.path.join(self.theme_dir, resolution)
        
        self._verify_paths()
    
    def _verify_paths(self):
        """Verify required directories exist"""
        if not os.path.isdir(self.video_path):
            raise FileNotFoundError(f"Video directory not found: {self.video_path}")
        if not os.path.isdir(self.theme_path):
            raise FileNotFoundError(f"Theme directory not found: {self.theme_path}")
        
        print(f"\n✓ Videos: {self.video_path}")
        print(f"✓ Themes: {self.theme_path}")
    
    def connect(self):
        """Connect to LCD"""
        self.lcd = SamaSM360Serial(self.serial_port)
        self.lcd.connect()
        return self.lcd
    
    def list_videos(self):
        """List all available videos"""
        videos = {}
        try:
            for video_file in sorted(os.listdir(self.video_path)):
                if video_file.endswith('.mp4'):
                    videos[video_file[:-4]] = video_file  # name without extension
        except FileNotFoundError:
            pass
        return videos
    
    def stop_playback(self):
        """Send STOP command"""
        print("\n⏹️  STOPPING current playback...")
        
        stop_packet = bytearray(250)
        stop_packet[0] = 0xaa  # STOP command
        stop_packet[1] = 0xef
        stop_packet[2] = 0x69
        stop_packet[6] = 0x01
        
        print_hex_dump("STOP (0xaa)", bytes(stop_packet[:20]))
        
        self.lcd.ser.write(bytes(stop_packet))
        time.sleep(0.3)
        
        response = self.lcd._read_response(timeout=0.3)
        if response:
            resp_text = response.decode('utf-8', errors='ignore').strip('\x00')
            print(f"  Response: {resp_text[:50]}")
        
        print("  ✓ Stop sent")
        return True
    
    def load_video(self, filename: str):
        """
        Load video by testing all paths
        Sequence from captured log:
        1. Try /tmp/video (0x16)
        2. Try /root/video (0x17)
        3. Try /mnt/SDCARD/video (0x1d) - usually works
        
        Returns True if found, False otherwise
        """
        print(f"\n📹 LOADING video: {filename}")
        print("   Testing paths...")
        
        for path, path_selector in self.VIDEO_PATHS.items():
            full_path = f"{path}/{filename}"
            print(f"\n   Trying: {full_path} (0x{path_selector:02x})")
            
            # Build LOAD packet (0x6e)
            load_packet = bytearray(250)
            load_packet[0] = 0x6e  # LOAD VIDEO command
            load_packet[1] = 0xef
            load_packet[2] = 0x69
            load_packet[6] = path_selector  # Path selector
            
            # Add path string
            path_bytes = full_path.encode('utf-8')[:230]
            load_packet[10:10+len(path_bytes)] = path_bytes
            
            print_hex_dump(f"LOAD (0x6e) path {path_selector:02x}", bytes(load_packet[:40]))
            
            self.lcd.ser.write(bytes(load_packet))
            time.sleep(0.3)
            
            response = self.lcd._read_response(timeout=0.5)
            if response:
                resp_text = response.decode('utf-8', errors='ignore').strip('\x00')
                print(f"      Response: {resp_text[:50]}")
                
                # Check if it's a file size (success!) or "0" (not found)
                if resp_text != '0':
                    print(f"      ✓ Found! File size: {resp_text}")
                    return True
                else:
                    print(f"      ✗ Not found on this path")
            
            time.sleep(0.2)
        
        print(f"\n   ❌ Video not found on any path: {filename}")
        return False
    
    def get_status(self):
        """Get device status (0x64 command)"""
        print("\n📊 POLLING status...")
        
        status_packet = bytearray(250)
        status_packet[0] = 0x64  # STATUS command
        status_packet[1] = 0xef
        status_packet[2] = 0x69
        status_packet[6] = 0x01
        
        self.lcd.ser.write(bytes(status_packet))
        time.sleep(0.2)
        
        response = self.lcd._read_response(timeout=0.5)
        if response:
            status_text = response.decode('utf-8', errors='ignore').strip('\x00')
            print(f"  Status: {status_text}")
            return status_text
        
        return None
    
    def poll_status_until_ready(self, max_polls=10, delay=0.5):
        """Poll status multiple times until video is loaded"""
        print(f"\n⏱️  Polling status ({max_polls} times, {delay}s interval)...")
        
        for i in range(max_polls):
            status = self.get_status()
            if status and status != '0':
                print(f"  Poll {i+1}/{max_polls}: ✓ Ready")
                time.sleep(delay)
            else:
                print(f"  Poll {i+1}/{max_polls}: waiting...")
                time.sleep(delay)
        
        return True
    
    def play_video(self):
        """
        Play loaded video
        Command: 0x78 with subcommand 0x01
        """
        print("\n▶️  PLAYING video...")
        
        play_packet = bytearray(250)
        play_packet[0] = 0x78  # PLAY command
        play_packet[1] = 0xef
        play_packet[2] = 0x69
        play_packet[6] = 0x01  # Play flag/subcommand
        
        print_hex_dump("PLAY (0x78)", bytes(play_packet[:20]))
        
        self.lcd.ser.write(bytes(play_packet))
        time.sleep(0.3)
        
        response = self.lcd._read_response(timeout=0.3)
        if response:
            resp_text = response.decode('utf-8', errors='ignore').strip('\x00')
            print(f"  Response: {resp_text[:50]}")
        
        print("  ✓ Play sent")
        return True
    
    def play_video_sequence(self, filename: str):
        """
        Complete playback sequence:
        1. STOP
        2. LOAD VIDEO (test all paths)
        3. POLL STATUS
        4. PLAY
        """
        print(f"\n{'='*70}")
        print(f"  🎬 PLAYING: {filename}")
        print(f"{'='*70}\n")
        
        # Step 1: STOP
        if not self.stop_playback():
            return False
        time.sleep(0.5)
        
        # Step 2: LOAD VIDEO
        if not self.load_video(filename):
            return False
        time.sleep(0.5)
        
        # Step 3: POLL STATUS
        if not self.poll_status_until_ready(max_polls=10, delay=0.1):
            return False
        time.sleep(0.3)
        
        # Step 4: PLAY
        if not self.play_video():
            return False
        time.sleep(0.3)
        
        print(f"\n✅ Playback sequence complete: {filename}\n")
        return True
    
    def interactive_menu(self):
        """Interactive video player menu"""
        while True:
            print("\n" + "="*70)
            print("  📺 SAMA SM360 LCD - Video Player")
            print("="*70)
            print(f"  Resolution: {self.resolution}")
            print(f"  Port: {self.serial_port}")
            print("="*70)
            print("\n  1. List videos")
            print("  2. Play video (interactive)")
            print("  3. Play video (direct name)")
            print("  4. Stop playback")
            print("  5. Get device status")
            print("  6. Test path /tmp/video")
            print("  7. Test path /root/video")
            print("  8. Test path /mnt/SDCARD/video")
            print("  9. Disconnect and exit")
            print("\n" + "="*70)
            
            choice = input("\n  Select option: ").strip()
            
            if choice == '1':
                # List videos
                videos = self.list_videos()
                if videos:
                    print(f"\n  📁 Available videos ({len(videos)} found):")
                    for name, filename in videos.items():
                        print(f"    ✓ {name} ({filename})")
                else:
                    print("  ❌ No videos found")
            
            elif choice == '2':
                # Interactive selection
                videos = self.list_videos()
                if videos:
                    video_list = list(videos.items())
                    print(f"\n  📁 Select video:")
                    for i, (name, _) in enumerate(video_list, 1):
                        print(f"    {i}. {name}")
                    
                    try:
                        idx = int(input("\n  Select number: ")) - 1
                        if 0 <= idx < len(video_list):
                            filename = video_list[idx][1]
                            self.play_video_sequence(filename)
                            input("\n  Press Enter to continue...")
                    except ValueError:
                        print("  ❌ Invalid input")
                else:
                    print("  ❌ No videos found")
            
            elif choice == '3':
                # Direct name
                filename = input("\n  Enter video filename (e.g., theme04.mp4): ").strip()
                if filename:
                    if not filename.endswith('.mp4'):
                        filename += '.mp4'
                    self.play_video_sequence(filename)
                    input("\n  Press Enter to continue...")
            
            elif choice == '4':
                # Stop
                if self.lcd:
                    self.stop_playback()
                    input("\n  Press Enter to continue...")
            
            elif choice == '5':
                # Status
                if self.lcd:
                    self.get_status()
                    input("\n  Press Enter to continue...")
            
            elif choice == '6':
                # Test /tmp
                filename = input("\n  Enter filename to test in /tmp/video: ").strip()
                if not filename.endswith('.mp4'):
                    filename += '.mp4'
                
                packet = bytearray(250)
                packet[0] = 0x6e
                packet[1] = 0xef
                packet[2] = 0x69
                packet[6] = 0x16
                path_bytes = f"/tmp/video/{filename}".encode('utf-8')[:230]
                packet[10:10+len(path_bytes)] = path_bytes
                
                print(f"\n  Testing: /tmp/video/{filename}")
                self.lcd.ser.write(bytes(packet))
                time.sleep(0.3)
                response = self.lcd._read_response(timeout=0.5)
                if response:
                    print(f"  Response: {response.decode('utf-8', errors='ignore').strip()}")
                
                input("\n  Press Enter to continue...")
            
            elif choice == '7':
                # Test /root
                filename = input("\n  Enter filename to test in /root/video: ").strip()
                if not filename.endswith('.mp4'):
                    filename += '.mp4'
                
                packet = bytearray(250)
                packet[0] = 0x6e
                packet[1] = 0xef
                packet[2] = 0x69
                packet[6] = 0x17
                path_bytes = f"/root/video/{filename}".encode('utf-8')[:230]
                packet[10:10+len(path_bytes)] = path_bytes
                
                print(f"\n  Testing: /root/video/{filename}")
                self.lcd.ser.write(bytes(packet))
                time.sleep(0.3)
                response = self.lcd._read_response(timeout=0.5)
                if response:
                    print(f"  Response: {response.decode('utf-8', errors='ignore').strip()}")
                
                input("\n  Press Enter to continue...")
            
            elif choice == '8':
                # Test /mnt/SDCARD
                filename = input("\n  Enter filename to test in /mnt/SDCARD/video: ").strip()
                if not filename.endswith('.mp4'):
                    filename += '.mp4'
                
                packet = bytearray(250)
                packet[0] = 0x6e
                packet[1] = 0xef
                packet[2] = 0x69
                packet[6] = 0x1d
                path_bytes = f"/mnt/SDCARD/video/{filename}".encode('utf-8')[:230]
                packet[10:10+len(path_bytes)] = path_bytes
                
                print(f"\n  Testing: /mnt/SDCARD/video/{filename}")
                self.lcd.ser.write(bytes(packet))
                time.sleep(0.3)
                response = self.lcd._read_response(timeout=0.5)
                if response:
                    print(f"  Response: {response.decode('utf-8', errors='ignore').strip()}")
                
                input("\n  Press Enter to continue...")
            
            elif choice == '9':
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
        print("\n" + "="*70)
        print("  🚀 SAMA SM360 LCD - Video Player")
        print("  Based on captured log analysis")
        print("="*70)
        
        # Get serial port
        serial_port = input("\n  Enter serial port (default: COM4): ").strip() or 'COM4'
        
        # Get resolution
        print("\n  Available resolutions:")
        resolution_list = list(VideoPlayer.RESOLUTIONS.items())
        for i, (name, folder) in enumerate(resolution_list, 1):
            print(f"    {i}. {name} ({folder})")
        
        try:
            res_num = int(input("\n  Select resolution (default: 4): ").strip() or '4') - 1
            if 0 <= res_num < len(resolution_list):
                resolution = resolution_list[res_num][1]
            else:
                resolution = '480480r'
        except ValueError:
            resolution = '480480r'
        
        # Create player
        player = VideoPlayer(serial_port=serial_port, resolution=resolution)
        
        # Connect
        print("\n  🔌 Connecting to LCD...")
        player.connect()
        print("  ✓ Connected")
        
        # Initialize
        print("  ⚙️  Initializing LCD...")
        player.lcd.initialize()
        print("  ✓ Ready")
        
        # Run menu
        player.interactive_menu()
        
    except KeyboardInterrupt:
        print("\n\n  ⏸️  Interrupted by user")
    except Exception as e:
        print(f"\n  ❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
