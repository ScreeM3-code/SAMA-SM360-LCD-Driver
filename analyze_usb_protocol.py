#!/usr/bin/env python3
"""
Analyze USB protocol from pcapng to identify file transfer mechanism
"""
import subprocess
import json
import re

# Get frame info from Wireshark
pcapng_file = r"c:\Users\ScreeM\Documents\GitHub\SAMA-SM360-LCD-Driver\Sama\usb run2.pcapng"

# List of frames to analyze
frames_to_check = [3153, 3167, 3173, 4647, 4648, 4649, 4653, 4841]

print("=" * 80)
print("USB PROTOCOL ANALYSIS - FILE TRANSFER SEQUENCE")
print("=" * 80)

for frame_num in frames_to_check:
    # Get frame details
    cmd = [
        r"C:\Program Files\Wireshark\tshark.exe",
        "-r", pcapng_file,
        "-Y", f"frame.number=={frame_num}",
        "-T", "fields",
        "-e", "frame.time_relative",
        "-e", "usb.src",
        "-e", "usb.dst",
        "-e", "frame.len"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        parts = result.stdout.strip().split('\t')
        if len(parts) >= 4:
            time_rel, src, dst, frame_len = parts[0], parts[1] if len(parts) > 1 else "?", parts[2] if len(parts) > 2 else "?", parts[3] if len(parts) > 3 else "?"
            
            # Get hex dump
            cmd_hex = [
                r"C:\Program Files\Wireshark\tshark.exe",
                "-r", pcapng_file,
                "-Y", f"frame.number=={frame_num}",
                "-x"
            ]
            
            result_hex = subprocess.run(cmd_hex, capture_output=True, text=True)
            hex_lines = result_hex.stdout.split('\n')[:10]  # First 10 lines
            
            print(f"\n[FRAME {frame_num}] Time: {time_rel}s | Len: {frame_len} bytes | {src} → {dst}")
            print("-" * 80)
            for line in hex_lines:
                if line.strip():
                    print(f"  {line}")

print("\n" + "=" * 80)
print("KEY FINDINGS:")
print("=" * 80)
print("""
1. Frame 3153 (6.817775s) = Initial LOAD command (277 bytes)
2. Frame 3167 (6.855342s) = Response with device info: "chs_5inch.dev1_rom1.89"
3. Frames 4647-4653 = File transfer trigger sequence:
   - Frame 4647: Setup command with parameters
   - Frame 4648: Small URB_BULK out (27 bytes)
   - Frame 4649: Command (3777 bytes, mostly zeros)
   - Frame 4653: ACTUAL FILE DATA (123099 bytes)
4. Pattern in commands: 01 03 [changing bytes]
""")
