# SAMA SM360 - Theme Manager & START/STOP Control

## 🎯 Vue d'ensemble

Le LCD SAMA SM360 fonctionne avec un **système de sélection/transfert/démarrage** pour les thèmes vidéo:

```
[STOP] → [SELECT] → [TRANSFER] → [START]
  ↑         ↑          ↑           ↑
  Stop la  Sélectionne Transfère  Démarre
  lecture  le thème    la vidéo   la lecture
```

**Point important**: On ne peut pas charger un nouveau thème sans d'abord arrêter le thème actuel!

---

## 📋 Séquence Complète de Changement de Thème

### Étape 1: STOP
```python
stop_current_playback(lcd)
# Envoie commande STOP (0xaa) au LCD
# Arrête la vidéo actuelle
```

**Commande**: `0xaa ef 69 00 00 00 01 ...`

### Étape 2: SELECT
```python
select_theme(lcd, "theme06")
# Envoie commande SELECT (0xbb) avec nom du thème
# Prépare le LCD pour recevoir les données
```

**Commande**: `0xbb ef 69 00 00 00 01 [theme_name]`

### Étape 3: TRANSFER
```python
transfer_theme(lcd, "/mnt/SDCARD/video/theme06.mp4")
# Envoie commande TRANSFER (0xcc) avec chemin vidéo
# Initie le transfert de la vidéo vers le LCD
```

**Commande**: `0xcc ef 69 00 00 00 1d [video_path]`

### Étape 4: START
```python
start_playback(lcd)
# Envoie commande START (0xdd) avec flag play
# Démarre la lecture du thème
```

**Commande**: `0xdd ef 69 00 00 00 01 01 ...`

---

## 🎬 Utilisation

### Mode Interactif

```bash
python theme_manager.py
```

Menu:
1. **List themes** - Affiche les thèmes disponibles et leurs chemins vidéo
2. **Change theme (interactive)** - Menu de sélection interactif
3. **Change theme (direct)** - Entrer le nom du thème manuellement
4. **Stop playback** - Arrête la vidéo actuelle
5. **Get status** - Affiche l'état du LCD

### Code Direct

```python
from theme_manager import change_theme_complete
from sama_sm360_serial import SamaSM360Serial

lcd = SamaSM360Serial('COM4')
lcd.connect()
lcd.initialize()

# Changer vers theme06
change_theme_complete(lcd, "theme06")

lcd.close()
```

---

## 📁 Extraction Automatique des Chemins

Le script extrait automatiquement les chemins vidéo à partir des fichiers de config:

**Fichiers config**: `Theme/theme*.txt` (fichiers sérialisés .NET)

**Contenu**:
```
Theme/theme06.txt
  ├─ Theme name: "theme06"
  ├─ Config path: C:\Program Files\...\theme06.turtheme
  ├─ Video path: /mnt/SDCARD/video/theme06.mp4  ← Extrait automatiquement
  └─ Preview image: [PNG binary data]
```

**Fonction**:
```python
from sama_sm360_serial import extract_video_path_from_config

video_path = extract_video_path_from_config("Theme/theme06.txt")
# Retourne: "/mnt/SDCARD/video/theme06.mp4"
```

---

## 🔍 Codes de Commande (Tentatives)

| Commande | Code | Subcommand | Data | Notes |
|----------|------|-----------|------|-------|
| STOP | 0xaa | 0x01 | N/A | Arrête la lecture courante |
| SELECT | 0xbb | 0x01 | Theme name | Sélectionne un thème |
| TRANSFER | 0xcc | 0x1d | Video path | Transfère la vidéo |
| START | 0xdd | 0x01 | 0x01 (flag) | Démarre la lecture |

**⚠️ À VÉRIFIER**: Ces codes sont basés sur des patterns observés. À confirmer avec le vrai périphérique!

---

## 🧪 Testing

### Test 1: Liste des thèmes
```bash
python -c "from sama_sm360_serial import list_available_themes; list_available_themes()"
```

Sortie:
```
📁 Available themes:
  ✓ theme04: /mnt/SDCARD/video/theme04.mp4
  ✓ theme06: /mnt/SDCARD/video/theme06.mp4
  ✓ theme17: /mnt/SDCARD/video/theme17.mp4
```

### Test 2: Changement complet
```python
from theme_manager import change_theme_complete
from sama_sm360_serial import SamaSM360Serial

lcd = SamaSM360Serial('COM4')
lcd.connect()
lcd.initialize()

# Séquence complète
success = change_theme_complete(lcd, "theme04")
if success:
    print("✅ Thème changé avec succès!")
else:
    print("❌ Changement échoué")

lcd.close()
```

---

## 🔧 Paramètres à Ajuster

Basé sur le log du test, certains paramètres peuvent nécessiter ajustement:

### Timeouts
```python
# Si le LCD ne répond pas assez vite:
TRANSFER_TIMEOUT = 1.0  # Au lieu de 0.5
```

### Réessais
```python
# Si le TRANSFER échoue:
MAX_RETRIES = 3
for attempt in range(MAX_RETRIES):
    transfer_theme(lcd, video_path)
    time.sleep(0.5)
```

### Délais Inter-commandes
```python
# Si les commandes arrivent trop vite:
time.sleep(0.2)  # Entre chaque commande
```

---

## 📊 Structure du Log Attendu

Quand tu exécutes le changement de thème, tu devrais voir:

```
======================================================================
  🎨 CHANGING THEME: theme06
======================================================================

⏹️  STOPPING current playback...
  ✓ Stop command sent

📁 SELECTING theme: theme06...
  ✓ Theme selected: theme06

📤 TRANSFERRING video to device...
   Path: /mnt/SDCARD/video/theme06.mp4
  ✓ Transfer initiated

▶️  STARTING playback...
  ✓ Playback started

✅ Theme change complete: theme06 is now playing!
```

---

## 🐛 Débugging

### Voir les hex dumps détaillés
```python
# Pour chaque commande, ajoute:
print_hex_dump("Ma commande", packet)
# Affiche les bytes en hex et ASCII
```

### Capturer les réponses
```python
response = lcd._read_response(timeout=0.5)
if response:
    print(f"Raw: {response.hex()}")
    print(f"Text: {response.decode('utf-8', errors='ignore')}")
```

### Vérifier l'état du LCD
```python
status = lcd.get_status()
if status:
    print(f"Status: {status['raw']}")
    # Format: "val1-val2-val3-val4-val5-val6"
    # Permet de vérifier si le LCD est actif
```

---

## ✅ Checklist de Test

- [ ] Connecter le LCD sur COM4 (ou autre port)
- [ ] Lancer le script: `python theme_manager.py`
- [ ] Option 1: Lister les thèmes (vérifier extraction)
- [ ] Option 2: Sélectionner un thème du menu
- [ ] Vérifier les hex dumps dans la console
- [ ] Vérifier l'état de la LED/écran du LCD
- [ ] Documenter les réponses reçues
- [ ] Ajuster les codes de commande si nécessaire

---

## 📝 Notes

1. **Les chemins vidéo** sont stockés dans les fichiers `.txt` du dossier `Theme/`
2. **Les codes 0xaa, 0xbb, 0xcc, 0xdd** sont des hypothèses - à confirmer!
3. **Le système est récursif**: Si START échoue, il faut renvoyer STOP avant de retenter
4. **Le timing est critique**: Les délais entre les commandes sont importants

---

## 🔮 Prochaines Étapes

1. Confirmer les codes de commande réels (0xaa, 0xbb, 0xcc, 0xdd)
2. Tester avec un vrai périphérique connecté
3. Décoder les réponses exactes pour chaque commande
4. Ajouter gestion des erreurs et retry logic
5. Tester le changement rapide de thèmes
6. Adapter pour Linux (/dev/ttyACM0)

