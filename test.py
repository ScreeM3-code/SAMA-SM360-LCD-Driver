#!/usr/bin/env python3
"""Recréation du Theme04 via protocole série"""

from sama_sm360_serial import SamaSM360Serial
import time
from datetime import datetime


def main():
    lcd = SamaSM360Serial('COM4')

    if not lcd.connect():
        print("❌ Connexion échouée")
        return

    if not lcd.initialize():
        print("❌ Init échouée")
        return

    print("\n🎨 Recréation du Theme04...")

    # 1. Afficher heure (position 174, 678)
    now = datetime.now()
    time_str = now.strftime("%H:%M")
    lcd.display_text(time_str, 174, 678, font_size=60, color_rgb=(255, 255, 255))
    time.sleep(0.5)

    # 2. Afficher jour de la semaine (position 252, 1020)
    day_str = now.strftime("%a")  # "Thu", "Fri"...
    lcd.display_text(day_str, 252, 1020, font_size=38, color_rgb=(255, 255, 255))
    time.sleep(0.5)

    # 3. Afficher date (position 252, 1020 pour mois, 56, 1020 pour jour)
    month_str = now.strftime("%m")
    day_num = now.strftime("%d")
    lcd.display_text(month_str, 252, 1020, font_size=38)
    lcd.display_text("/", 253, 1021, font_size=38)
    lcd.display_text(day_num, 56, 1020, font_size=38)
    time.sleep(0.5)

    # 4. Afficher température CPU (position 58, 613)
    lcd.display_data("CPUTEMP", "47", 58, 613, font_size=38, unit="°")
    time.sleep(0.5)

    # 5. Afficher vitesse pompe (position 237, 594)
    lcd.display_data("WATERPUMP", "1406", 237, 594, font_size=32, unit="R")

    print("\n✅ Theme04 recréé ! L'écran affiche-t-il quelque chose ?")
    print("Appuyez sur Ctrl+C pour arrêter...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Arrêt...")
        lcd.close()


if __name__ == '__main__':
    main()