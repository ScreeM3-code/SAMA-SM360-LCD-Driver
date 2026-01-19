#!/usr/bin/env python3
"""
SAMA SM360 LCD - Theme & Video Testing Script
Complete initialization + video playback testing
"""

import serial
import time
from sama_sm360_serial import SamaSM360Serial, print_hex_dump

def list_available_themes():
    """Display available theme files"""
    print("\n📁 Available themes on SD card:")
    print("   theme04.mp4  - Theme 4")
    print("   theme06.mp4  - Theme 6 ✅ (Tested)")
    print("   theme17.mp4  - Theme 17")
    print("\nNote: Files should be in /mnt/SDCARD/video/")

def test_initialization_sequence(lcd):
    """Test step-by-step initialization"""
    print("\n" + "="*70)
    print("  🔧 INITIALIZATION SEQUENCE")
    print("="*70)
    
    print("\n[1/3] Handshake (0x01)")
    packet = lcd._build_packet(cmd=0x01, subcmd=0x01, value=0x00)
    packet = bytearray(packet)
    packet[10] = 0xc5
    packet[11] = 0xd3
    
    print_hex_dump("Handshake packet", bytes(packet[:30]))
    lcd.ser.write(bytes(packet))
    time.sleep(0.1)
    
    response = lcd._read_response(timeout=0.5)
    if response:
        device_id = response.decode('utf-8', errors='ignore').strip('\x00')
        print(f"  ✅ Device ID: {device_id}\n")
    
    print("[2/3] Secondary Init (0x79)")
    packet = lcd._build_packet(cmd=0x79, subcmd=0x01, value=0x00)
    print_hex_dump("Secondary init packet", packet[:30])
    lcd.ser.write(packet)
    time.sleep(0.05)
    print("  ✅ Sent\n")
    
    print("[3/3] Tertiary Init (0x96)")
    packet = lcd._build_packet(cmd=0x96, subcmd=0x01, value=0x00)
    print_hex_dump("Tertiary init packet", packet[:30])
    lcd.ser.write(packet)
    time.sleep(0.1)
    
    response = lcd._read_response(timeout=0.5)
    if response:
        status = response.decode('utf-8', errors='ignore').strip('\x00')
        print(f"  ✅ Status: {status}\n")
    
    print("✅ Initialization complete!\n")

def test_video_load_sequence(lcd, video_name):
    """Test video loading with all three path variants"""
    print("\n" + "="*70)
    print(f"  🎬 VIDEO LOADING TEST: {video_name}")
    print("="*70)
    
    paths = [
        (0x16, f"/tmp/video/{video_name}", "Temporary storage"),
        (0x17, f"/root/video/{video_name}", "Linux home directory"),
        (0x1d, f"/mnt/SDCARD/video/{video_name}", "SD Card (RECOMMENDED)")
    ]
    
    for subcmd, path, description in paths:
        print(f"\nAttempt: {description}")
        print(f"  Path: {path}")
        print(f"  Subcommand: 0x{subcmd:02x}")
        
        # Build load packet
        load_packet = bytearray(250)
        load_packet[0] = 0x6e  # Load video
        load_packet[1] = 0xef
        load_packet[2] = 0x69
        load_packet[6] = subcmd
        
        path_bytes = path.encode('utf-8')
        load_packet[10:10 + len(path_bytes)] = path_bytes
        
        print_hex_dump(f"Load packet (0x{subcmd:02x})", bytes(load_packet[:40]))
        
        lcd.ser.write(bytes(load_packet))
        time.sleep(0.1)
        
        response = lcd._read_response(timeout=0.3)
        if response:
            try:
                response_text = response.decode('utf-8', errors='ignore').strip('\x00')
                file_size = int(response_text)
                
                if file_size > 0:
                    print(f"  ✅ FOUND! File size: {file_size} bytes ({file_size/1024/1024:.1f} MB)")
                    print(f"\n🎯 SUCCESS: Video found at {description}")
                    return subcmd, path
                else:
                    print(f"  ❌ Not found (response: 0)")
            except ValueError:
                print(f"  ⚠️  Unexpected response: {response_text}")
    
    print(f"\n❌ Video not found on any path")
    return None, None

def test_play_and_verify(lcd, subcmd, path, video_name):
    """Play video and monitor status"""
    print("\n" + "="*70)
    print(f"  ▶️  PLAYING VIDEO: {video_name}")
    print("="*70)
    
    # Build play packet
    play_packet = bytearray(250)
    play_packet[0] = 0x78  # Play command
    play_packet[1] = 0xef
    play_packet[2] = 0x69
    play_packet[6] = subcmd
    play_packet[7] = 0x01  # Play flag
    
    path_bytes = path.encode('utf-8')
    play_packet[10:10 + len(path_bytes)] = path_bytes
    
    print_hex_dump(f"Play packet", bytes(play_packet[:40]))
    
    lcd.ser.write(bytes(play_packet))
    time.sleep(0.2)
    
    response = lcd._read_response(timeout=0.3)
    if response:
        resp_text = response.decode('utf-8', errors='ignore').strip('\x00')
        print(f"Response: {resp_text[:50]}")
    
    print("\n🎬 Video playback initiated on LCD screen")
    print("   Check the physical device to verify playback")

def test_brightness_sequence(lcd):
    """Test brightness control"""
    print("\n" + "="*70)
    print("  🔆 BRIGHTNESS TEST")
    print("="*70)
    
    levels = [
        (0xFF, "Maximum (100%)"),
        (0x80, "Medium (50%)"),
        (0x40, "Low (25%)"),
        (0xFF, "Back to Maximum"),
    ]
    
    for value, description in levels:
        print(f"\n{description}: 0x{value:02x}")
        
        packet = lcd._build_packet(cmd=0x7b, subcmd=0x01, value=value)
        print_hex_dump(f"Brightness packet (0x{value:02x})", packet[:30])
        
        lcd.ser.write(packet)
        time.sleep(0.3)
        
        response = lcd._read_response(timeout=0.2)
        if response:
            print(f"  ✅ Device acknowledged")
        else:
            print(f"  ✓ Command sent (no response expected)")

def test_status_polling(lcd, count=5):
    """Poll device status multiple times"""
    print("\n" + "="*70)
    print(f"  📊 STATUS POLLING ({count} times)")
    print("="*70)
    
    for i in range(count):
        print(f"\nPoll #{i+1}:")
        
        status_packet = lcd._build_packet(cmd=0x64, subcmd=0x01, value=0x00)
        print_hex_dump(f"Status request packet", status_packet[:30])
        
        lcd.ser.write(status_packet)
        time.sleep(0.1)
        
        response = lcd._read_response(timeout=0.5)
        if response:
            try:
                status_text = response.decode('utf-8', errors='ignore').strip('\x00')
                print(f"  ✅ Status: {status_text}")
                
                # Try to parse values
                if '-' in status_text:
                    values = status_text.split('-')
                    print(f"     Values: {values}")
            except:
                print(f"  Response (hex): {response[:30].hex()}")
        
        time.sleep(0.3)

def interactive_menu(lcd):
    """Interactive test menu"""
    while True:
        print("\n" + "="*70)
        print("  SAMA SM360 LCD - THEME & VIDEO TESTING")
        print("="*70)
        print("\n1. Test initialization sequence")
        print("2. Test brightness control")
        print("3. Test video loading (theme06)")
        print("4. Test video loading (custom)")
        print("5. Test status polling")
        print("6. List available themes")
        print("7. Run complete theme sequence")
        print("8. Exit\n")
        
        choice = input("Select option (1-8): ").strip()
        
        if choice == "1":
            try:
                test_initialization_sequence(lcd)
            except Exception as e:
                print(f"❌ Error: {e}")
        
        elif choice == "2":
            try:
                test_brightness_sequence(lcd)
            except Exception as e:
                print(f"❌ Error: {e}")
        
        elif choice == "3":
            try:
                subcmd, path = test_video_load_sequence(lcd, "theme06.mp4")
                if subcmd:
                    test_play_and_verify(lcd, subcmd, path, "theme06")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        elif choice == "4":
            try:
                video_name = input("Enter video filename (e.g., theme04.mp4): ").strip()
                if video_name:
                    subcmd, path = test_video_load_sequence(lcd, video_name)
                    if subcmd:
                        test_play_and_verify(lcd, subcmd, path, video_name)
            except Exception as e:
                print(f"❌ Error: {e}")
        
        elif choice == "5":
            try:
                count = int(input("How many polls? (default 5): ").strip() or "5")
                test_status_polling(lcd, count)
            except Exception as e:
                print(f"❌ Error: {e}")
        
        elif choice == "6":
            list_available_themes()
        
        elif choice == "7":
            try:
                print("\nExecuting complete sequence:")
                print("1. Initialize")
                test_initialization_sequence(lcd)
                time.sleep(1)
                
                print("2. Set brightness to 80%")
                lcd.set_brightness(80)
                time.sleep(0.5)
                
                print("3. Load and play theme06")
                from sama_sm360_serial import test_complete_theme_sequence
                test_complete_theme_sequence(lcd, "theme06")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        elif choice == "8":
            print("\nExiting...")
            break
        
        else:
            print("Invalid choice")

def main():
    """Main entry point"""
    print("="*70)
    print("  SAMA SM360 LCD - THEME & VIDEO TESTING")
    print("  Complete hex-level analysis and debugging")
    print("="*70)
    
    # Auto-detect port
    import serial.tools.list_ports
    
    ports = list(serial.tools.list_ports.comports())
    sama_port = None
    
    print("\nAvailable COM ports:")
    for port in ports:
        print(f"  {port.device}: {port.description}")
        if '1A86' in port.hwid or 'SM360' in port.description or 'USB' in port.description:
            sama_port = port.device
            print(f"    ^ Detected SAMA SM360!")
    
    if not sama_port:
        sama_port = input("\nEnter COM port (e.g., COM4): ").strip() or "COM4"
    
    try:
        print(f"\n🔌 Connecting to {sama_port}...")
        lcd = SamaSM360Serial(sama_port)
        
        if not lcd.connect():
            print("❌ Failed to connect")
            return
        
        print("✅ Connected!")
        
        # Run interactive menu
        interactive_menu(lcd)
        
        lcd.close()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
