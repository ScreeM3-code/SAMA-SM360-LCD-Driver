#!/usr/bin/env python3
"""
SAMA SM360 LCD Driver - Video File Loader
Protocol: Send FILE_ID commands via USB/Serial, not raw MP4 files
"""

import serial
import time
import struct

class SAMASM360LCD:
    def __init__(self, port="COM4", baudrate=115200, timeout=1):
        """Initialize connection to LCD via COM port"""
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        
    def connect(self):
        """Open serial connection"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            print(f"✓ Connected to {self.port} @ {self.baudrate}baud")
            return True
        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("✓ Disconnected")
    
    def send_command(self, cmd_code: bytes, file_id: bytes = None, frame_size: int = 277):
        """
        Send a command to the LCD
        
        Args:
            cmd_code: Command code (e.g., b'\x01\x03' for LOAD VIDEO)
            file_id: File identifier bytes (3-4 bytes for video files)
            frame_size: Total USB frame size (277, 3777, 123099 bytes, etc.)
        """
        if not self.serial or not self.serial.is_open:
            print("✗ Not connected")
            return False
        
        # Build the command frame
        frame = bytearray(frame_size)
        
        # Command code (always 01 03 for video loading)
        frame[0:2] = cmd_code
        
        # File ID (if provided)
        if file_id:
            frame[2:2+len(file_id)] = file_id
        
        # Rest is zeros (padding) - bytearray is already zero-initialized
        
        try:
            self.serial.write(bytes(frame))
            print(f"✓ Sent command: {cmd_code.hex()} {file_id.hex() if file_id else '(no ID)'} ({frame_size} bytes)")
            return True
        except Exception as e:
            print(f"✗ Send failed: {e}")
            return False
    
    def read_response(self, timeout: float = 2):
        """
        Read response from LCD
        
        Returns: bytes of response or None if timeout
        """
        if not self.serial or not self.serial.is_open:
            return None
        
        try:
            start_time = time.time()
            response = bytearray()
            
            while time.time() - start_time < timeout:
                if self.serial.in_waiting > 0:
                    response.extend(self.serial.read(self.serial.in_waiting))
                    time.sleep(0.01)  # Give more data time to arrive
                else:
                    if response:
                        break
                time.sleep(0.01)
            
            if response:
                print(f"✓ Received: {response.hex()}")
                return bytes(response)
            return None
        except Exception as e:
            print(f"✗ Read failed: {e}")
            return None
    
    def identify_device(self):
        """Get device identification information"""
        print("\n[IDENTIFY DEVICE]")
        # Command to get device info: 01 03 FA
        self.send_command(b'\x01\x03', b'\xfa', frame_size=277)
        response = self.read_response()
        if response:
            # Look for ASCII text in response
            try:
                text = response.decode('utf-8', errors='ignore')
                print(f"Device info: {text}")
            except:
                pass
        return response
    
    def load_video(self, file_id: bytes):
        """
        Load a video file by ID
        
        Args:
            file_id: 3-4 bytes that identify the video file
        """
        print(f"\n[LOAD VIDEO] File ID: {file_id.hex()}")
        # Command: 01 03 [FILE_ID]
        self.send_command(b'\x01\x03', file_id, frame_size=123099)
        response = self.read_response()
        return response
    
    def stop(self):
        """Stop playback (based on earlier protocol analysis: 0xAA)"""
        print("\n[STOP]")
        self.send_command(b'\xaa', frame_size=277)
        return True
    
    def play(self):
        """Start/resume playback (0x78)"""
        print("\n[PLAY]")
        self.send_command(b'\x78', frame_size=277)
        return True
    
    def get_status(self):
        """Get playback status (0x64)"""
        print("\n[GET STATUS]")
        self.send_command(b'\x64', frame_size=277)
        response = self.read_response()
        return response


def main():
    """Example usage"""
    lcd = SAMASM360LCD(port="COM4")
    
    if not lcd.connect():
        return
    
    try:
        # Identify device
        lcd.identify_device()
        time.sleep(0.5)
        
        # Stop any existing playback
        lcd.stop()
        time.sleep(0.5)
        
        # Load video file (example FILE_ID from capture)
        # This is FILE_ID from frame 4653 in usb run2.pcapng
        lcd.load_video(bytes.fromhex('c0e001'))
        time.sleep(1)
        
        # Check status
        lcd.get_status()
        time.sleep(0.5)
        
        # Play
        lcd.play()
        time.sleep(5)
        
        # Stop
        lcd.stop()
        
    finally:
        lcd.disconnect()


if __name__ == "__main__":
    main()
