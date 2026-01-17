#!/usr/bin/env python3
"""Test brightness control"""

from sama_sm360 import SamaSM360
import time


def test_brightness():
    lcd = SamaSM360()

    if not lcd.initialize():
        print("Init failed!")
        return

    print("\n🔆 Testing brightness control...")

    # Test sequence
    levels = [0, 25, 50, 75, 100, 50]

    for level in levels:
        print(f"\nSetting brightness to {level}%...")
        lcd.set_brightness(level)
        time.sleep(2)

    print("\n✅ Test complete!")
    lcd.close()


if __name__ == '__main__':
    test_brightness()