#!/usr/bin/env python3
"""
SAMA SM360 - Guide de Capture USB pour identifier les VRAIES commandes
Ce script vous aide à capturer les bonnes séquences USB
"""

import os
import sys
from datetime import datetime


class USBCaptureGuide:
    """Guide interactif pour capturer les commandes USB correctes"""

    SCENARIOS_TO_CAPTURE = {
        "background_change": {
            "title": "Changement de couleur de fond",
            "steps": [
                "1. Démarrer Wireshark avec filtre 'usb.device_address == 21'",
                "2. Dans SAMA, changer la couleur de fond (ex: bleu → rouge)",
                "3. Stopper la capture",
                "4. Sauver comme 'capture_background_change.pcapng'",
            ],
            "expected_commands": [
                "Probablement 0xc8 avec données RGB",
                "Chercher patterns: RGB values (0x00-0xFF pour R, G, B)",
            ]
        },

        "text_display": {
            "title": "Affichage de texte",
            "steps": [
                "1. Démarrer Wireshark",
                "2. Dans SAMA, afficher un texte simple (ex: 'TEST')",
                "3. Stopper la capture",
                "4. Sauver comme 'capture_text_display.pcapng'",
            ],
            "expected_commands": [
                "Probablement 0xc8 avec subcommand 0x02",
                "Chercher le texte 'TEST' en ASCII dans les données",
            ]
        },

        "video_stop": {
            "title": "ARRÊT d'une vidéo en cours",
            "steps": [
                "1. Lancer une vidéo dans SAMA",
                "2. Attendre 2 secondes",
                "3. Démarrer Wireshark",
                "4. ARRÊTER la vidéo dans SAMA",
                "5. Stopper la capture immédiatement",
                "6. Sauver comme 'capture_video_stop.pcapng'",
            ],
            "expected_commands": [
                "La VRAIE commande STOP (pas 0xaa!)",
                "Chercher une commande juste avant 'media_stop' response",
            ]
        },

        "video_change": {
            "title": "Changement de vidéo (theme04 → theme06)",
            "steps": [
                "1. Lancer theme04.mp4 dans SAMA",
                "2. Attendre que la vidéo joue",
                "3. Démarrer Wireshark",
                "4. Changer pour theme06.mp4 dans SAMA",
                "5. Stopper quand la nouvelle vidéo démarre",
                "6. Sauver comme 'capture_video_change.pcapng'",
            ],
            "expected_commands": [
                "Séquence complète: STOP → LOAD → PLAY",
                "Identifier les VRAIES commandes utilisées",
            ]
        },

        "image_static": {
            "title": "Affichage d'image statique",
            "steps": [
                "1. Démarrer Wireshark",
                "2. Dans SAMA, afficher une image PNG/JPG",
                "3. Stopper la capture",
                "4. Sauver comme 'capture_image_display.pcapng'",
            ],
            "expected_commands": [
                "Commande inconnue pour images statiques",
                "Chercher données binaires (PNG/JPG header)",
                "Ou chercher un path vers l'image",
            ]
        },
    }

    def print_menu(self):
        """Affiche le menu des scénarios à capturer"""
        print("\n" + "=" * 80)
        print("  📸 GUIDE DE CAPTURE USB - SAMA SM360")
        print("=" * 80)
        print("\n⚠️  IMPORTANT: Vous devez capturer ces scénarios DANS LE LOGICIEL SAMA!")
        print("    Les commandes 0xaa, 0xbb, 0xcc, 0xdd étaient des HYPOTHÈSES FAUSSES.\n")

        for i, (key, scenario) in enumerate(self.SCENARIOS_TO_CAPTURE.items(), 1):
            print(f"{i}. {scenario['title']}")

        print(f"{len(self.SCENARIOS_TO_CAPTURE) + 1}. Analyser une capture existante")
        print(f"{len(self.SCENARIOS_TO_CAPTURE) + 2}. Quitter")
        print("\n" + "=" * 80)

    def show_scenario(self, scenario_key):
        """Affiche les instructions pour un scénario"""
        scenario = self.SCENARIOS_TO_CAPTURE[scenario_key]

        print("\n" + "=" * 80)
        print(f"  📋 SCÉNARIO: {scenario['title']}")
        print("=" * 80)

        print("\n📝 ÉTAPES À SUIVRE:")
        for step in scenario['steps']:
            print(f"   {step}")

        print("\n🔍 CE QU'ON CHERCHE:")
        for expected in scenario['expected_commands']:
            print(f"   • {expected}")

        print("\n" + "=" * 80)
        print("💡 APRÈS LA CAPTURE:")
        print("   1. Ouvrir le fichier .pcapng dans Wireshark")
        print("   2. Filtre: usb.device_address == 21 && usb.data_len > 0")
        print("   3. Exporter les URB_BULK out vers un fichier texte")
        print("   4. Partager le fichier pour analyse")
        print("=" * 80)

    def analyze_capture(self, capture_file):
        """Guide d'analyse d'une capture"""
        print("\n" + "=" * 80)
        print("  🔬 ANALYSE DE CAPTURE")
        print("=" * 80)

        if not os.path.exists(capture_file):
            print(f"\n❌ Fichier non trouvé: {capture_file}")
            return

        print(f"\n📁 Fichier: {capture_file}")
        print("\n🔍 COMMANDES À CHERCHER DANS WIRESHARK:")
        print("\n1. FILTRE GÉNÉRAL:")
        print("   usb.device_address == 21 && usb.data_len > 0")

        print("\n2. CHERCHER LES PATTERNS:")
        print("   • Bytes de commande (offset 0): 0x01, 0x79, 0x96, 0x7b, 0x6e, 0x78, 0xc8...")
        print("   • Magic header (offset 1-2): ef 69")
        print("   • Subcommand (offset 6): Variable")

        print("\n3. POUR CHAQUE URB_BULK out:")
        print("   a. Noter le Frame number")
        print("   b. Noter le timestamp")
        print("   c. Copier les premiers 50 bytes en hex")
        print("   d. Chercher des strings ASCII (texte, chemins)")

        print("\n4. EXPORTER:")
        print("   File → Export Packet Dissections → As Plain Text")
        print("   Options: 'Packet summary line' + 'Packet bytes'")

        print("\n" + "=" * 80)

    def run(self):
        """Lance le guide interactif"""
        while True:
            self.print_menu()

            try:
                choice = input("\nSélectionner une option: ").strip()
                choice_num = int(choice)

                scenarios = list(self.SCENARIOS_TO_CAPTURE.keys())

                if 1 <= choice_num <= len(scenarios):
                    scenario_key = scenarios[choice_num - 1]
                    self.show_scenario(scenario_key)
                    input("\nAppuyer sur Entrée pour continuer...")

                elif choice_num == len(scenarios) + 1:
                    capture_file = input("\nChemin du fichier .pcapng: ").strip()
                    self.analyze_capture(capture_file)
                    input("\nAppuyer sur Entrée pour continuer...")

                elif choice_num == len(scenarios) + 2:
                    print("\n👋 Au revoir!")
                    break

                else:
                    print("\n❌ Option invalide")

            except ValueError:
                print("\n❌ Entrer un nombre valide")
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted")
                break


def print_current_status():
    """Affiche l'état actuel du reverse engineering"""
    print("\n" + "=" * 80)
    print("  📊 ÉTAT ACTUEL DU REVERSE ENGINEERING")
    print("=" * 80)

    print("\n✅ COMMANDES CONFIRMÉES (capturées et testées):")
    commands_confirmed = [
        ("0x01", "Handshake", "Device ID response", "✅ Fonctionne"),
        ("0x79", "Init Secondary", "No response", "✅ Fonctionne"),
        ("0x96", "Init Tertiary", "'media_stop'", "✅ Fonctionne"),
        ("0x7b", "Set Brightness", "Ack", "✅ Fonctionne"),
        ("0x6e", "Load Video", "File size", "✅ Fonctionne"),
        ("0x78", "Play Video", "Unknown", "✅ Fonctionne"),
        ("0x64", "Get Status", "Status values", "✅ Fonctionne"),
    ]

    for cmd, name, response, status in commands_confirmed:
        print(f"   {cmd} ({name:20s}) → {response:20s} {status}")

    print("\n⚠️  COMMANDES HYPOTHÉTIQUES (JAMAIS CAPTURÉES):")
    commands_hypothetical = [
        ("0xaa", "STOP", "Hypothèse non confirmée"),
        ("0xbb", "SELECT", "Hypothèse non confirmée"),
        ("0xcc", "TRANSFER", "Hypothèse non confirmée"),
        ("0xdd", "START", "Hypothèse non confirmée"),
    ]

    for cmd, name, note in commands_hypothetical:
        print(f"   {cmd} ({name:20s}) → {note}")

    print("\n❓ COMMANDES MENTIONNÉES MAIS NON TESTÉES:")
    commands_mentioned = [
        ("0xc8", "Display Text/Color", "Mentionné dans README, structure inconnue"),
        ("0x82", "Unknown (Post-média)", "Observée mais fonction inconnue"),
        ("0x86", "Unknown (Pré-texte)", "Observée mais fonction inconnue"),
        ("0x2c", "Clear Buffer?", "Pattern de virgules répétées"),
    ]

    for cmd, name, note in commands_mentioned:
        print(f"   {cmd} ({name:20s}) → {note}")

    print("\n" + "=" * 80)
    print("💡 PROCHAINES ÉTAPES:")
    print("=" * 80)
    print("1. Capturer 0xc8 (affichage texte/couleur) avec différents paramètres")
    print("2. Identifier la VRAIE commande STOP (pas 0xaa)")
    print("3. Tester changement de vidéo sans arrêt préalable")
    print("4. Capturer affichage d'images statiques")
    print("5. Analyser la commande 0x82 (post-média)")
    print("=" * 80)


def main():
    """Point d'entrée principal"""
    print("\n" + "=" * 80)
    print("  🚀 SAMA SM360 - GUIDE DE CAPTURE USB")
    print("  Identification des VRAIES commandes de contrôle")
    print("=" * 80)

    print("\n⚠️  AVERTISSEMENT:")
    print("   Les commandes 0xaa, 0xbb, 0xcc, 0xdd dans theme_manager.py")
    print("   étaient des HYPOTHÈSES. Elles n'ont JAMAIS été observées dans")
    print("   les captures USB réelles.")
    print("\n   Ce guide vous aide à capturer les VRAIES commandes utilisées")
    print("   par le logiciel SAMA officiel.\n")

    print_current_status()

    input("\nAppuyer sur Entrée pour continuer...")

    guide = USBCaptureGuide()
    guide.run()


if __name__ == '__main__':
    main()