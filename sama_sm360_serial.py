#!/usr/bin/env python3
"""
Sama SM360 LCD Driver - Version Finale Optimisée
Protocole : 0x6F (Upload), 0x78 (Play), 0x87 (Sync)
Basé sur l'analyse des logs DMS (Device Monitoring Studio)
"""

import serial
import time
import sys
from pathlib import Path

# --- CONFIGURATION ---
BAUDRATE = 115200
PACKET_SIZE = 250
# Dossier par défaut pour les vidéos
SCRIPT_DIR = Path(__file__).parent
VIDEO_DIR = SCRIPT_DIR / "Video sama" / "480480r"


class SamaLCD:
    def __init__(self, port='COM4'):
        self.port = port
        self.ser = None

    def connect(self):
        try:
            self.ser = serial.Serial(port=self.port, baudrate=BAUDRATE, timeout=0.1)
            # On ne fait pas de reset auto ici, on laisse l'utilisateur décider
            print(f"✅ Connecté sur {self.port}")
            return True
        except Exception as e:
            print(f"❌ Erreur de connexion : {e}")
            return False

    def send_post_playback(self):
        """
        Send post-playback command (0x86)
        Discovered: Sent after play_video_success
        """
        packet = self._build_packet(cmd=0x86, subcmd=0x01, value=0x00)
        self.ser.write(packet)
        print("  ✓ Post-playback command sent (0x86)")
        time.sleep(0.1)

    def flush_lcd_memory(self):
        """Envoie la séquence d'arrêt et de reset avant un upload"""
        print("🧹 Nettoyage de la mémoire du LCD...")

        # 1. Commande STOP (0xAA) - On l'envoie pour libérer le fichier actuel
        stop_cmd = bytearray([0xAA, 0xEF, 0x69] + [0x00] * 7 + [0x01] + [0x00] * (250 - 11))
        self.ser.write(stop_cmd)
        time.sleep(0.2)

        # 2. Séquence de RESET (0x2C) - Le fameux remplissage que tu as vu
        # On envoie plusieurs paquets de 250 octets de 0x2C
        for _ in range(3):
            self.ser.write(bytes([0x2C] * 250))
            time.sleep(0.05)

        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        print("✔️ Mémoire fléchée. Prêt pour le nouvel upload.")

    def upload_and_play_video(self, video_path):
        if not video_path.exists():
            print("❌ Fichier introuvable.")
            return

        # --- ÉTAPE 0 : NETTOYAGE ---
        self.flush_lcd_memory()

        filename = video_path.name
        remote_path = f"/mnt/SDCARD/video/{filename}"
        path_bytes = remote_path.encode('utf-8')
        path_len = len(path_bytes)

        # --- ÉTAPE 1 : OUVERTURE DU FICHIER (0x6F) ---
        print(f"🚀 Ouverture du fichier distant : {filename}")
        header = bytearray([0x6F, 0xEF, 0x69])
        header.extend(path_len.to_bytes(4, byteorder='big'))
        header.extend([0x00, 0x00, 0x00])
        header.extend(path_bytes)
        self.ser.write(header)

        # On attend un peu que le LCD crée le fichier sur la SD
        time.sleep(0.5)

        # --- ÉTAPE 2 : ENVOI PAR PETITS PAQUETS ---
        file_size = video_path.stat().st_size
        sent_bytes = 0
        print(f"📦 Transfert en cours (Vitesse réduite pour stabilité)...")

        with open(video_path, "rb") as f:
            while True:
                # On réduit la taille des blocs à 1KB au lieu de 8KB
                chunk = f.read(1024)
                if not chunk:
                    break

                self.ser.write(chunk)
                sent_bytes += len(chunk)

                # PAUSE CRUCIALE : On laisse 2ms entre chaque KB pour que
                # le processeur du LCD puisse écrire sur la carte SD.
                time.sleep(0.002)

                if sent_bytes % 51200 == 0:  # Update barre de progression tous les 50KB
                    percent = (sent_bytes / file_size) * 100
                    sys.stdout.write(f"\r   Progression : {percent:.1f}%")
                    sys.stdout.flush()

        print("\n✅ Transfert terminé avec succès.")



    def read_feedback(self, timeout=1.0):
        """Lit les messages envoyés par l'écran (logs internes du LCD)"""
        start = time.time()
        captured = ""
        while (time.time() - start) < timeout:
            if self.ser.in_waiting:
                data = self.ser.read(self.ser.in_waiting).decode('utf-8', errors='ignore')
                captured += data
            time.sleep(0.02)
        return captured

    def _build_packet(self, cmd: int, subcmd: int, value: int = 0) -> bytes:
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

    def send_reset(self):
        """Commande Manuelle (0x2C) pour vider les buffers en cas de bug"""
        print("\n🧹 Nettoyage du tampon (Reset 0x2C)...")
        reset_packet = bytes([0x2C] * PACKET_SIZE)
        self.ser.write(reset_packet)
        self.ser.flush()
        time.sleep(0.5)
        self.ser.reset_input_buffer()
        print("✔️ Tampons réinitialisés.")

    def set_brightness(self, level):
        """Règle la luminosité (0-100)"""
        val = int((level / 100.0) * 255)
        packet = bytearray(PACKET_SIZE)
        packet[0:3] = [0x7B, 0xEF, 0x69]
        packet[10] = val
        self.ser.write(packet)
        print(f"🔆 Luminosité : {level}%")

    def close(self):
        if self.ser:
            self.ser.close()


def menu():
    lcd = SamaLCD(port='COM4')
    if not lcd.connect():
        return

    while True:
        print("\n" + "=" * 40)
        print("      SAMA SM360 - CONTROLEUR VIDÉO")
        print("=" * 40)
        print("1. Lister et Envoyer une Vidéo (.mp4)")
        print("2. Changer Luminosité")
        print("3. play")
        print("8. RESET MANUEL (0x2C)")
        print("0. Quitter")

        choice = input("\nChoix : ")

        if choice == "1":
            if not VIDEO_DIR.exists():
                print(f"❌ Dossier {VIDEO_DIR} non trouvé.")
                continue

            videos = list(VIDEO_DIR.glob("*.mp4"))
            if not videos:
                print("Aucun fichier .mp4 trouvé.")
                continue

            print("\nVidéos disponibles :")
            for i, v in enumerate(videos, 1):
                print(f"{i}. {v.name}")

            try:
                idx = int(input("\nNuméro de la vidéo : ")) - 1
                if 0 <= idx < len(videos):
                    lcd.upload_and_play_video(videos[idx])
            except ValueError:
                print("Entrée invalide.")

        elif choice == "2":
            try:
                lum = int(input("Luminosité (0-100) : "))
                lcd.set_brightness(lum)
            except ValueError:
                pass

        elif choice == "3":
            try:
                lcd.send_post_playback()
            except ValueError:
                pass

        elif choice == "8":
            lcd.send_reset()

        elif choice == "0":
            print("Bye!")
            break

    lcd.close()


if __name__ == "__main__":
    menu()