# SAMA SM360 - Référence Complète des Commandes

## 📋 Tableau Récapitulatif

| Cmd | Nom | Subcommand | Value | Réponse | Status | Notes |
|-----|-----|-----------|-------|---------|--------|-------|
| 0x01 | Handshake | 0x01 | 0xc5,0xd3 (offset 10-11) | Device ID string | ✅ | Doit être premier; spécial bytes requis |
| 0x79 | Init Secondary | 0x01 | 0x00 | None | ✅ | Post-handshake |
| 0x96 | Init Tertiary | 0x01 | 0x00 | "media_stop" | ✅ | Indique prêt pour média |
| 0x7b | Set Brightness | 0x01 | 0x00-0xFF | Ack | ✅ | 0x00=0%, 0xFF=100% |
| 0x7d | Type-5 (Unknown) | 0x05 | 0x00-0xFF | Ack? | ⚠️ | Toujours après brightness; fonction inconnue |
| 0x64 | Get Status | 0x01 | 0x00 | "val1-val2-..." | ✅ | Format texte, séparé par tirets |
| 0x6e | Load Video | 0x16/0x17/0x1d | - | File size or 0 | ✅ | Subcommand = chemin; data = filepath UTF-8 |
| 0x78 | Play Video | 0x16/0x17/0x1d | 0x01 | (Unknown) | ✅ | Subcommand doit matcher LOAD; chemin identique |
| 0x82 | Unknown (Verify?) | 0x01 | 0x00 | None | ⚠️ | Post-commande média |
| 0x86 | Unknown | 0x01 | 0x00 | None | ⚠️ | Pré-affichage texte? |
| 0xc8 | Display Text/Color | 0x0e/0x00/0x02 | - | None | ⚠️ | Affichage texte/couleur; structure complexe |
| 0x2c | Clear Buffer? | - | - | None | ⚠️ | Paquets répétés; fonction inconnue |

---

## 🔌 Structure de Paquet Standard

```
Byte  Description              Value/Range    Notes
────────────────────────────────────────────────────────
0     Command                  0x00-0xFF      Commande principale
1-2   Magic Header             0xef 0x69      Toujours présent
3-5   Reserved/Padding         0x00 0x00 0x00 Réservé
6     Subcommand/Type          0x00-0xFF      Varie par commande
7-9   Reserved/Padding         0x00 0x00 0x00 Réservé
10    Primary Value            0x00-0xFF      Dépend de la commande
11+   Padding/Data             0x00 ou DATA   Rempli jusqu'à 250 bytes
```

**Taille fixe**: 250 bytes (avec padding null)

---

## 🎬 Sous-commandes Load/Play (0x6e, 0x78)

### Path Selectors:
```
0x16 → /tmp/video/
0x17 → /root/video/
0x1d → /mnt/SDCARD/video/ (RECOMMANDÉ - plus rapide)
```

### Format données (offset 10+):
```
[PATH_STRING]\0[padding]\0...\0
```
- String UTF-8 du chemin complet
- Null-terminated
- Le reste padding jusqu'à 250 bytes

### Réponses:
```
Load (0x6e):
  - "0"          → Fichier non trouvé
  - "1152859"    → Taille en bytes (fichier trouvé!)

Play (0x78):
  - (observable dans les logs - à déterminer)
```

---

## 🔄 Séquence Recommended

### Démarrage + Video

```python
# 1. Handshake (identifie le device)
send(0x01, subcmd=0x01, special_bytes=[0xc5, 0xd3])
wait_for_response()  # "chs_5inch.dev1_rom1.89"

# 2. Init secondaire
send(0x79, subcmd=0x01)
sleep(50ms)

# 3. Init tertiaire
send(0x96, subcmd=0x01)
wait_for_response()  # "media_stop"

# 4. Configuration affichage
send(0x7b, subcmd=0x01, value=0x80)  # Brightness 50%
sleep(50ms)

# 5. Type-5 (mystère)
send(0x7d, subcmd=0x05, value=0x80)  # Same value as brightness?
sleep(50ms)

# 6. Charger vidéo
send(0x6e, subcmd=0x1d, data="/mnt/SDCARD/video/theme06.mp4")
wait_for_response()  # Should be file size

# 7. Jouer vidéo
send(0x78, subcmd=0x1d, data="/mnt/SDCARD/video/theme06.mp4", flag=0x01)
sleep(200ms)

# Optional: Vérifier
send(0x82, subcmd=0x01)  # Verification/Sync?
```

### Code Python équivalent:

```python
from sama_sm360_serial import SamaSM360Serial

lcd = SamaSM360Serial('COM4')
lcd.connect()
lcd.initialize()  # Exécute handshake + init 2 + init 3

lcd.set_brightness(80)  # 0x7b
time.sleep(0.2)

# Type-5 command
lcd.send_command(0x7d, subcmd=0x05, value=0x80)
time.sleep(0.2)

# Load and play
lcd.load_and_play_video("theme06.mp4")
```

---

## 🔍 Parsing des Réponses

### Device ID (Handshake)
```
Raw bytes: 63 68 73 5f 35 69 6e 63 68 2e 64 65 76 31 5f 72 6f 6d 31 2e 38 39 00
ASCII: chs_5inch.dev1_rom1.89

Parse:
  Device type: chs_5inch
  Firmware: dev1_rom1.89
  Type code: chs_5inch → "Chasis 5 inch"?
```

### Status Response (0x64)
```
Raw bytes: 32 36 38 38 2d 31 34 32 30 2d 31 32 36 38 2d 31 32 32 38 38 30 2d 33 31 38 36 2d 31 31 39 36 39 34
ASCII: 2688-1420-1268-122880-3186-119694

Parse:
  values = "2688-1420-1268-122880-3186-119694".split('-')
  
  Hypothesis (basé sur AIODATA theme):
    val[0] = 2688    → CPU Fan RPM?
    val[1] = 1420    → GPU Fan RPM?
    val[2] = 1268    → Temp (×100) → 12.68°C
    val[3] = 122880  → Puissance/Fréquence?
    val[4] = 3186    → ?
    val[5] = 119694  → ?
```

### File Size Response (0x6e)
```
Raw bytes: 31 31 35 32 38 35 39 00
ASCII: 1152859

Parse:
  file_size = int("1152859") = 1,152,859 bytes = 1.1 MB ✓
  if file_size > 0:
    print("Fichier trouvé!")
  else:
    print("Fichier non trouvé")
```

---

## ⏱️ Timings Recommandés

```
Après initialization:       100-200ms avant next command
Après brightness change:    100-200ms avant next command
Après load video:           200-300ms avant play command
Après play video:           1000ms (vidéo commence)
Entre status polls:         200-500ms
```

---

## 🐛 Débugging Tips

### Capture HEX Dump
```python
def print_hex(title, data):
    print(f"\n{title}")
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32<=b<127 else '.' for b in chunk)
        print(f"  {i:03d}: {hex_str:<48} | {ascii_str}")

# Usage:
packet = lcd._build_packet(0x6e, 0x1d, 0)
print_hex("Load Video Packet", packet[:50])
```

### Vérifier connexion COM
```python
import serial.tools.list_ports

for port in serial.tools.list_ports.comports():
    print(f"{port.device}: {port.description}")
    print(f"  HWID: {port.hwid}")
    if '1A86' in port.hwid:
        print("  ^ SAMA SM360 detected!")
```

### Analyser réponses
```python
response = lcd._read_response(timeout=0.5)
if response:
    # Try text
    try:
        text = response.decode('utf-8', errors='ignore').strip('\x00')
        print(f"Text: {text}")
    except:
        pass
    
    # Show hex
    print(f"Hex: {response[:50].hex()}")
```

---

## 🔮 Commands à Investiguer

1. **0x82 (Verify/Sync)**
   - Envoyée post-media
   - Fonction réelle inconnue
   - Essayer avec différentes valeurs

2. **0x7d variations**
   - Essayer subcmd: 0x00-0xFF
   - Essayer value: 0x00-0xFF
   - Voir si affecte gamma/couleur

3. **0xc8 (Display)**
   - Structure complexe mentionnée dans README
   - Fond + texte
   - RGB + positionnement

4. **0x2c (Clear Buffer?)**
   - Paquets répétés
   - Possiblement reset/clear écran

5. **0x86 (Inconnu)**
   - Pré-affichage texte
   - Structure à déterminer

---

## 📝 Notes sur la Compatibilité Linux

### Port Serial
```python
# Windows
port = 'COM4'

# Linux
port = '/dev/ttyACM0'  # Adapter le numéro

# Auto-detect
import platform
if platform.system() == 'Linux':
    port = '/dev/ttyACM0'
else:
    port = 'COM4'
```

### Chemins fichiers
```
Windows: C:\videos\theme06.mp4
Linux:   /mnt/SDCARD/video/theme06.mp4
         (Adapter selon configuration)

Dans le protocole: Toujours utiliser chemins Linux!
```

### Permissions
```bash
# Linux: S'assurer que l'utilisateur peut accéder au port série
sudo usermod -a -G dialout $USER
# Puis se reconnecter
```

---

## ✅ Checklist Déploiement

- [ ] Tester sur Windows avec COM port
- [ ] Vérifier tous les timings
- [ ] Tester avec différents thèmes
- [ ] Implémenter gestion d'erreur réseau
- [ ] Adapter chemins pour Linux (/dev/ttyACM0)
- [ ] Créer version Linux-ready
- [ ] Documenter variations de firmware
- [ ] Tests de stress (requêtes répétées)

