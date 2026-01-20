

🎯 SAMA SM360 LCD Driver - Résumé des Découvertes
📊 Ce qu'on SAIT avec certitude
1. Communication Série (✅ CONFIRMÉ)
Port: COM4 (Windows) / /dev/ttyACM0 (Linux probable)
Baud Rate: 115200
Device: USB CDC/ACM (VendorID: 0x1A86, ProductID: 0xCA21)
Firmware: dev1_rom1.89
Type: chs_5inch (LCD 5 pouces)
2. Structure de Protocole (✅ DÉCODÉ)
[CMD] ef 69 00 00 00 [SUBCMD] [FLAGS] 00 00 [VALUE/DATA...] [padding à 250 bytes]
  ↑    ↑ Magic      ↑         ↑              ↑
  Cmd  Header      Subcmd    Flags          Données variables
3. Commandes Fonctionnelles (✅ TESTÉES)
Commande	Code	Usage	Status
Handshake	0x01	Init device	✅ Retourne "chs_5inch.dev1_rom1.89"
Init 2	0x79	Secondary init	✅ Pas de réponse
Init 3	0x96	Tertiary init	✅ Retourne "media_stop"
Brightness	0x7b	Contrôle luminosité 0-255	✅ FONCTIONNEL
Type-5	0x7d	Fonction inconnue	⚠️ Toujours après brightness
Get Status	0x64	Monitoring données	✅ Format "val1-val2-..."
Load Video	0x6e	Charger vidéo (par FILE_ID)	✅ 3 chemins possibles
Play Video	0x78	Jouer vidéo	✅ Après Load
Unknown	0x82	Post-commande	⚠️ Fonction inconnue

🎬 DÉCOUVERTE MAJEURE: Système de Fichiers Interne
Le LCD CONTIENT DÉJÀ les fichiers vidéo!
Ancien concept (FAUX):

❌ Transférer des MP4 bruts via USB
❌ Encoder/compresser des vidéos
❌ Envoyer 123KB de données
Réalité découverte (VRAI):

✅ Le LCD a un système Linux embarqué
✅ Les vidéos sont pré-stockées dans 3 chemins:
/mnt/SDCARD/video/ (priorité 1, le plus rapide)
/root/video/ (fallback)
/tmp/video/ (fallback temporaire)
✅ On envoie juste le chemin du fichier (commande 0x6e)
✅ Le LCD charge la vidéo depuis sa propre mémoire
Séquence Load Video (CONFIRMÉE)
python
# Tentative 1: /tmp
send(0x6e, subcmd=0x16, data="/tmp/video/theme06.mp4")
response: "0"  # NOT FOUND

# Tentative 2: /root
send(0x6e, subcmd=0x17, data="/root/video/theme06.mp4")
response: "0"  # NOT FOUND

# Tentative 3: /mnt/SDCARD ✅
send(0x6e, subcmd=0x1d, data="/mnt/SDCARD/video/theme06.mp4")
response: "1152859"  # FOUND! (taille = 1.1 MB)

# Puis Play
send(0x78, subcmd=0x1d, data="/mnt/SDCARD/video/theme06.mp4", flag=0x01)
# La vidéo commence à jouer
Sous-commandes pour les chemins:

0x16 → /tmp/video/
0x17 → /root/video/
0x1d → /mnt/SDCARD/video/ ⭐
🖼️ Images et Médias (⚠️ PARTIELLEMENT COMPRIS)
Ce qu'on NE fait PAS:
❌ Transfert pixel par pixel (pas de RGB bitmap raw)

❌ Streaming vidéo depuis PC
Ce qu'on fait VRAIMENT:
1. Vidéos (✅ CONFIRMÉ)
python
# Pas de transfert - juste référence au fichier déjà présent
lcd.load_video("/mnt/SDCARD/video/theme06.mp4")  # 0x6e
lcd.play_video()  # 0x78
2. Images Statiques (⚠️ HYPOTHÈSE FORTE)
Basé sur les captures, probablement même système:

python
# Hypothèse (à tester):
lcd.display_image("/mnt/SDCARD/images/logo.png", x=0, y=0)
# Commande probable: 0xc8 avec subcmd=0x00
Indices:

Commande 0xc8 observée pour affichage
Structure: c8 ef 69 00 0e 10 00 00 00 00 [data...]
Subcmd 0x0e avec flags 0x10 → probablement type "image"
Les images sont pré-chargées sur le LCD (comme les vidéos)
3. Texte + Fond Uni (⚠️ STRUCTURE À ANALYSER)
python
# Commande 0xc8 capture:
# c8 ef 69 00 0e 10 00 00 00 00 [RGB?] [position?] [texte UTF-8?]

# Hypothèse:
lcd.display_text("Sama 360", x=174, y=678, 
                 font_size=60, color=(255,255,255),
                 background=(0,255,255))  # Cyan
```

**Structure probable**:
```
[0]    0xc8          Command: Display
[1-2]  ef 69         Magic header
[6]    0x0e ou 0x02  Subcmd (0x0e=background+text, 0x02=text seul)
[7-8]  Flags         0x10 0x00
[9-11] RGB           Couleur fond/texte (3 bytes)
[12-13] Position     X,Y (little-endian, 2 bytes each)
[14]   Font size     Taille police
[15+]  String        Texte UTF-8 null-terminated
🎨 Thèmes et Fichiers de Configuration
Extraction des Chemins Vidéo (✅ FONCTIONNEL)
Les fichiers Theme/theme*.txt contiennent des objets .NET sérialisés avec:

Nom du thème
Chemin de config Windows (.turtheme)
Chemin vidéo Linux (encodé en binaire)
Preview PNG (données binaires)
Code d'extraction:

python
from sama_sm360_serial import extract_video_path_from_config

video_path = extract_video_path_from_config("Theme/theme06.txt")
# Retourne: "/mnt/SDCARD/video/theme06.mp4"
Regex utilisée:

python
pattern = rb'/mnt/SDCARD/video/theme\d{2}\.mp4'
# ou
pattern = rb'/mnt/SDCARD/video/\w+\.mp4'
📡 Monitoring et Status (✅ FONCTIONNEL)
Commande Get Status (0x64)
python
lcd.get_status()
# Réponse: "2688-1420-1268-122880-3186-119694"
Format: VALUE1-VALUE2-VALUE3-VALUE4-VALUE5-VALUE6

Interprétation probable (basée sur thèmes AIODATA):

Index	Valeur	Unité	Hypothèse
0	2688	RPM	Vitesse ventilateur CPU
1	1420	RPM	Vitesse ventilateur GPU
2	1268	°C×100	Température CPU (12.68°C)
3	122880	?	Puissance ou fréquence
4	3186	?	Métrique secondaire
5	119694	?	Données additionnelles
⏱️ Timing et Séquence (✅ VALIDÉ)
Séquence d'Initialisation Complète
python
1. Handshake (0x01)         → Response: Device ID
   time.sleep(0.05)
2. Init 2 (0x79)
   time.sleep(0.05)
3. Init 3 (0x96)            → Response: "media_stop"
   time.sleep(0.1)
4. Set Brightness (0x7b)
   time.sleep(0.1)
5. Type-5 (0x7d)
   time.sleep(0.1)
6. Get Status (0x64)        → Response: monitoring data
   time.sleep(0.2)
7. Load Video (0x6e)        → Response: file size
   time.sleep(0.2)
8. Play Video (0x78)
Timeouts recommandés:

Post-init: 100-200ms
Post-brightness: 100-200ms
Post-load: 200-300ms
Entre status polls: 200-500ms
🔧 Code Python Fonctionnel (✅ TESTÉ)
Driver Principal: sama_sm360_serial.py
python
from sama_sm360_serial import SamaSM360Serial

lcd = SamaSM360Serial('COM4')  # ou '/dev/ttyACM0' sous Linux

# Connexion
lcd.connect()
lcd.initialize()  # Handshake + Init 2 + Init 3

# Brightness (CONFIRMÉ FONCTIONNEL)
lcd.set_brightness(80)  # 0-100%

# Charger et jouer vidéo
lcd.load_and_play_video("theme06.mp4")
# Essaie automatiquement:
# 1. /mnt/SDCARD/video/theme06.mp4
# 2. /root/video/theme06.mp4
# 3. /tmp/video/theme06.mp4

# Get status
status = lcd.get_status()
print(status)  # {'raw': '2688-1420-...', 'values': [2688, 1420, ...]}

lcd.close()
```

---

## ❓ Ce qu'on NE SAIT PAS ENCORE

### 1. **Commande 0x7d (Type-5)** ⚠️
- Toujours envoyée après brightness
- Valeur souvent `0x80` (même que brightness)
- **Hypothèses**:
  - Gamma correction?
  - Mode d'affichage (normal/HDR)?
  - Confirmation brightness?

### 2. **Commande 0x82 (Post-Media)** ⚠️
- Envoyée après Load/Play
- Pas de réponse observable
- **Hypothèses**:
  - Verify playback status?
  - Sync command?
  - Cleanup/reset buffer?

### 3. **Commande 0xc8 (Display)** ⚠️
**Capture observée**:
```
c8 ef 69 00 0e 10 00 00 00 00 [data...] → Fond cyan + "Sama 360" + "12%"
```

**À déterminer**:
- Offset exact de la couleur RGB
- Offset et format de la position (X, Y)
- Offset du texte UTF-8
- Différence entre subcmd `0x0e`, `0x00`, `0x02`
- Format du font size

### 4. **Affichage Images Statiques** ❌
- Commande non identifiée (probablement variante de 0xc8)
- Format: chemin fichier? ou données binaires?
- Résolution supportée?
- Formats supportés (PNG, JPG, BMP)?

### 5. **Commande 0x86** ⚠️
```
86 ef 69 00 00 00 01 00 00 00 00 [padding...]
```
- Observée avant affichage texte
- **Hypothèse**: "Prepare display" ou "Clear screen"

### 6. **Commande 0x2c (Répété)** ⚠️
```
2c 2c 2c 2c 2c 2c... (250 bytes de virgules)
Hypothèse: Clear buffer ou reset display
🎯 Prochaines Étapes Recommandées
Priorité HAUTE
Analyser structure 0xc8 (fond + texte)
Capturer avec différentes couleurs
Capturer avec différents textes
Identifier offsets RGB, position, font size
Tester affichage images
Essayer commande 0xc8 avec chemin image
Essayer upload image (si possible)
Identifier formats supportés
Priorité MOYENNE
Décoder commandes mystère
0x7d: tester différentes valeurs
0x82: observer réponses
0x86: tester avant/après display
Implémenter affichage système
Parser status (0x64) correctement
Mapper aux données monitoring PC
Afficher CPU temp, GPU temp, etc.
Priorité BASSE
Optimisations Linux
Tester sur /dev/ttyACM0
Créer daemon systemd
Interface web de contrôle
📚 Fichiers du Projet
Drivers et Scripts
sama_sm360_serial.py - Driver principal ✅
test_brightness.py - Test luminosité ✅
test.py - Test affichage thème (work in progress)
sama_lcd_video_loader.py - Loader vidéo (obsolète, remplacé par serial)
Documentation
README.md - Vue d'ensemble du projet
COMMAND_REFERENCE.md - Référence des commandes
LOG_ANALYSIS.md - Analyse détaillée du log COM4
THEME_MANAGER_README.md - Gestion des thèmes
PROTOCOL_FINAL_DISCOVERY.md - Découverte FILE_ID
PROTOCOL_DISCOVERY.md - Analyse protocole USB
Captures
captures/ini*.txt - Captures séquences d'init
captures/15425 to 15460.txt - Capture USB URB
Theme/theme*.txt - Fichiers config thèmes
🏆 Conclusion
✅ Ce qui fonctionne MAINTENANT
Communication série stable (COM4 @ 115200)
Initialisation complète du LCD
Contrôle brightness (testé et validé)
Chargement et lecture de vidéos (par chemin)
Extraction chemins vidéo depuis configs
Get status monitoring
⚠️ Ce qui nécessite plus de travail
Affichage texte + fond (structure 0xc8 à décoder)
Affichage images statiques (commande à identifier)
Interprétation précise du status monitoring
Fonction réelle de 0x7d, 0x82, 0x86, 0x2c
🎯 Vision finale
Un driver Linux complet permettant:

✅ Contrôler luminosité
⚠️ Afficher texte personnalisé
❌ Afficher images
✅ Lire vidéos (pré-chargées)
⚠️ Afficher données monitoring (CPU, GPU, RAM, etc.)
❌ Graphiques/jauges dynamiques
❌ Interface web de configuration
Avancement global: 🟡 ~30% complété

