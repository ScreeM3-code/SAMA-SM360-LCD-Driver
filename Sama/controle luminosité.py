def set_brightness(self, brightness: int):
    """
    Set LCD brightness

    Args:
        brightness: 0-100 (will be converted to 0-255)
    """
    if not 0 <= brightness <= 100:
        raise ValueError("Brightness must be 0-100")

    # Convert 0-100 to 0-255
    brightness_value = int((brightness / 100.0) * 255)

    # Build monitoring packet with brightness
    packet = bytearray(277)

    # Header
    packet[0:2] = struct.pack('<H', 277)
    packet[2:4] = struct.pack('<H', 0x1080)  # Cmd type
    packet[4:8] = b'\x00\x00\x00\x00'  # Timestamp
    packet[8:10] = b'\xff\xff'
    packet[10:12] = b'\x00\x00'
    packet[12:14] = b'\x00\x00'
    packet[14:16] = struct.pack('<H', 265)  # Payload length

    # Payload
    packet[16] = 0x00  # Command
    packet[17:22] = b'\x02\x00\x0a\x00\x01'
    packet[22] = 0x03  # Subcommand
    packet[23] = 0xfa  # Data type
    packet[24:28] = b'\x00\x00\x00'

    packet[28] = 0x7b  # Flag (can be 0x01 or 0x7b)
    packet[29] = 0xef  # Byte 1
    packet[30] = 0x69  # Byte 2
    packet[31] = 0x00

    packet[32:36] = b'\x00\x01\x00\x00\x00'

    # ★ SET BRIGHTNESS HERE ★
    packet[36] = brightness_value

    packet[37:40] = b'\x00\x00\x00'
    # Rest is padding (already 0x00)

    try:
        # Send brightness packet
        self.dev.write(ENDPOINT_BULK_OUT, bytes(packet))
        print(f"  ✓ Brightness set to {brightness}% (0x{brightness_value:02x})")

        # Send acknowledgement
        ack = self._build_packet(
            cmd_type=0x1080,
            command=0x01,
            params=b'\x02\x00\x0a\x00\x01\x03\x00\x00\x00\x00'
        )
        self.dev.write(ENDPOINT_BULK_OUT, ack)

        return True

    except usb.core.USBError as e:
        print(f"  ❌ Failed to set brightness: {e}")
        return False


def update_monitoring(self, cpu_temp: int, gpu_temp: int, fan_rpm: int, brightness: int = 100):
    """
    Update all monitoring data including temperatures and brightness

    Args:
        cpu_temp: CPU temperature in °C
        gpu_temp: GPU temperature in °C
        fan_rpm: Fan speed in RPM
        brightness: LCD brightness 0-100
    """
    brightness_value = int((brightness / 100.0) * 255)

    packet = bytearray(277)

    # Header (same as above)
    packet[0:2] = struct.pack('<H', 277)
    packet[2:4] = struct.pack('<H', 0x1080)
    packet[4:8] = b'\x00\x00\x00\x00'
    packet[8:10] = b'\xff\xff'
    packet[10:12] = b'\x00\x00'
    packet[12:14] = b'\x00\x00'
    packet[14:16] = struct.pack('<H', 265)

    # Payload
    packet[16] = 0x00
    packet[17:22] = b'\x02\x00\x0a\x00\x01'
    packet[22] = 0x03
    packet[23] = 0xfa
    packet[24:28] = b'\x00\x00\x00'

    # Temperature data (hypothesis - may need adjustment)
    packet[28] = 0x01
    packet[29] = cpu_temp & 0xFF  # CPU temp
    packet[30] = gpu_temp & 0xFF  # GPU temp (or could be something else)
    packet[31] = 0x00

    packet[32:36] = b'\x00\x01\x00\x00\x00'

    # Brightness
    packet[36] = brightness_value

    # Fan RPM (might be at different offset)
    # packet[37:41] = struct.pack('<I', fan_rpm)  # To be confirmed

    try:
        self.dev.write(ENDPOINT_BULK_OUT, bytes(packet))

        # Acknowledgement
        ack = self._build_packet(
            cmd_type=0x1080,
            command=0x01,
            params=b'\x02\x00\x0a\x00\x01\x03\x00\x00\x00\x00'
        )
        self.dev.write(ENDPOINT_BULK_OUT, ack)

        print(f"  ✓ Monitoring updated: CPU={cpu_temp}°C, GPU={gpu_temp}°C, "
              f"RPM={fan_rpm}, Brightness={brightness}%")
        return True

    except usb.core.USBError as e:
        print(f"  ❌ Failed to update monitoring: {e}")
        return False