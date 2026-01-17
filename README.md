# SAMA SM360 LCD Driver - Reverse Engineering
## Projet de Driver Linux pour Écran LCD AIO 5 pouces

---

## 📋 INFORMATIONS MATÉRIEL

### Device USB
- **Vendor ID**: `0x1a86` (QinHeng Electronics)
- **Product ID**: `0xca21` (UsbMonitor)
- **Nom**: Sama SM360 / UsbMonitor
- **Serial**: CT21INCH
- **Type**: LCD AIO 5 pouces (chs_5inch)
- **Firmware**: dev1_rom1.89

### Configuration USB
- **Classe**: CDC (Communications Device Class) + CDC Data
- **Interface 0**: CDC/ACM (Abstract Control Model)
  - Endpoint 0x81 IN (Interrupt)
- **Interface 1**: CDC Data
  - Endpoint 0x82 IN (Bulk)
  - Endpoint 0x03 OUT (Bulk)
- **Baud Rate**: 115200 (0x01c200)
- **MaxPower**: 500mA

### Connexion
- **Port physique**: Header USB 9-pin interne (USB_E12)
- **Ports COM virtuels**: 
  - COM3 (créé en premier, peu utilisé)
  - COM4 (port principal de communication)

---

## 🔬 PROTOCOLE DE COMMUNICATION

### Structure des Packets

```
[CMD] ef 69 00 00 00 [SUBCMD] [FLAGS] 00 00 [DATA...]
  |    |  |              |        |            |
  |    |  |              |        |            +-- Données variables (texte, chemins, valeurs)
  |    |  |              |        +--------------- Flags (0x00, 0x01, 0x05, etc.)
  |    |  |              +------------------------ Sous-commande
  |    |  +--------------------------------------- Padding fixe
  |    +------------------------------------------ Magic header (toujours 0xef 0x69)
  +----------------------------------------------- Byte de commande principale
```

**Taille standard**: 250 bytes (avec padding à 0x00)

### Magic Header
- Tous les packets commencent par: `[CMD] ef 69`
- Le header `ef 69` est **constant** et identifie le protocole Sama

---

## 🎛️ COMMANDES DÉCOUVERTES

### ✅ Commandes Fonctionnelles (Testées)

#### **0x01** - Handshake / Initialization
```
01 ef 69 00 00 00 01 00 00 00 c5 d3 [padding...]
```
- **Usage**: Premier packet envoyé lors de l'initialisation
- **Sous-commande**: 0x01
- **Données spéciales**: 0xc5 0xd3 (à l'offset 10-11)
- **Réponse du LCD**: "chs_5inch.dev1_rom1.89"

#### **0x79** - Init Secondaire
```
79 ef 69 00 00 00 01 00 00 00 00 [padding...]
```
- **Usage**: Deuxième packet d'initialisation
- **Sous-commande**: 0x01

#### **0x96** - Init Tertiaire
```
96 ef 69 00 00 00 01 00 00 00 00 [padding...]
```
- **Usage**: Troisième packet d'initialisation
- **Sous-commande**: 0x01
- **Réponse du LCD**: "media_stop"

#### **0x7b** - Set Brightness ✅ FONCTIONNEL
```
7b ef 69 00 00 00 01 00 00 00 [VALUE] [padding...]
                              ^^^^^^^^
                              Offset 10: Brightness 0x00-0xFF (0-255)
```
- **Usage**: Contrôle de la luminosité de l'écran
- **Sous-commande**: 0x01
- **Valeur**: 0x00 (0%) à 0xFF (100%)
- **Exemple**: 0x80 = 128 = 50% brightness
- **Status**: ✅ **TESTÉ ET FONCTIONNEL**

#### **0x7d** - Commande Type 5
```
7d ef 69 00 00 00 05 00 00 00 80 [padding...]
                  ^^          ^^
                  Subcmd=5    Value=0x80
```
- **Usage**: Fonction inconnue, toujours envoyée après brightness
- **Sous-commande**: 0x05
- **Valeur**: Souvent 0x80

#### **0x64** - Get Status / Monitoring Request
```
64 ef 69 00 00 00 01 00 00 00 00 [padding...]
```
- **Usage**: Demande d'état / données de monitoring
- **Sous-commande**: 0x01
- **Réponse**: Format texte avec valeurs séparées par "-"
- **Exemple réponse**: "2688-1420-1268-122880-1128-121752"
  - Possiblement: CPU temp, GPU temp, RPM, ou autres métriques

#### **0x6e** - Set Video Path / Load Media
```
6e ef 69 00 00 00 [SUBCMD] 00 00 00 [PATH_STRING] [padding...]
                  ^^^^^^^^          ^^^^^^^^^^^^^^^^
                  Subcmd variant     Chemin du fichier vidéo
```
- **Usage**: Spécifier le chemin d'un fichier vidéo à charger
- **Sous-commandes observées**:
  - `0x16`: `/tmp/video/theme06.mp4`
  - `0x17`: `/root/video/theme06.mp4`
  - `0x1d`: `/mnt/SDCARD/video/theme06.mp4`
- **Format**: String UTF-8 terminée par 0x00
- **Note**: Le LCD cherche le fichier dans différents chemins

#### **0x78** - Play Video (avec flags)
```
78 ef 69 00 00 00 1d 01 00 00 [PATH_STRING] [padding...]
                  ^^  ^^
                  Subcmd Flag
```
- **Usage**: Jouer une vidéo (variant avec flag)
- **Sous-commande**: 0x1d (chemin SD card)
- **Flag**: 0x01
- **Réponse du LCD**: "play_video_success"

#### **0x82** - Commande Inconnue
```
82 ef 69 00 00 00 01 00 00 00 00 [padding...]
```
- **Usage**: Fonction inconnue
- **Observée**: Après lecture vidéo

#### **0x86** - Commande Inconnue
```
86 ef 69 00 00 00 01 00 00 00 00 [padding...]
```
- **Usage**: Fonction inconnue
- **Observée**: Avant affichage texte/fond uni

#### **0xc8** - Display Background + Text ⚠️ À ANALYSER
```
c8 ef 69 00 0e 10 00 00 00 00 00 00 [DATA...] [padding...]
            ^^  ^^
            |   Flag 0x10
            Subcmd 0x0e
```
- **Usage**: Affichage fond de couleur uni + texte
- **Sous-commande**: 0x0e
- **Flags**: 0x10 0x00
- **Données**: Couleur RGB + texte (format exact à déterminer)
- **Exemple capturé**: Fond cyan + "Sama 360" + "12%"
- **Status**: ⚠️ **STRUCTURE À ANALYSER**

#### **0x2c** (Répété) - Clear / Reset?
```
2c 2c 2c 2c 2c 2c... (250 bytes de virgules)
```
- **Usage**: Possiblement clear screen ou reset buffer
- **Observé**: Avant affichage de nouveau contenu

---

## 📊 SÉQUENCE D'INITIALISATION

### Séquence Complète (Testée)
```
1. Handshake (0x01) → Réponse: "chs_5inch.dev1_rom1.89"
2. Init secondaire (0x79)
3. Init tertiaire (0x96) → Réponse: "media_stop"
4. Set brightness (0x7b)
5. Commande type 5 (0x7d)
6. Get status (0x64) → Réponse: valeurs de monitoring
```

### Notes sur l'Init
- Les commandes CONTROL (ctrl_transfer) **échouent** sur headers USB mais ce n'est **pas bloquant**
- Seuls les BULK transfers (endpoints 0x03 OUT et 0x82 IN) sont nécessaires
- Le LCD répond de manière asynchrone sur endpoint 0x82 IN

---

## ✅ FONCTIONNALITÉS IMPLÉMENTÉES

### 1. ✅ Contrôle de la Luminosité
- **Commande**: 0x7b
- **Range**: 0-100%
- **Status**: Pleinement fonctionnel
- **Code**: Implémenté dans `sama_sm360_serial.py`

### 2. ✅ Initialisation du Device
- **Séquence**: 0x01 → 0x79 → 0x96
- **Status**: Fonctionnel
- **Code**: Méthode `initialize()`

### 3. ✅ Lecture de l'ID du Device
- **Commande**: 0x01
- **Réponse**: "chs_5inch.dev1_rom1.89"
- **Status**: Fonctionnel

### 4. ⚠️ Lecture du Status
- **Commande**: 0x64
- **Réponse**: Format texte avec valeurs séparées
- **Status**: Fonctionne mais **interprétation des valeurs inconnue**

---

## 🚧 FONCTIONNALITÉS À IMPLÉMENTER

### Priorité HAUTE

#### 1. ⚠️ Affichage Texte + Fond Uni
- **Commande**: 0xc8
- **Status**: Commande identifiée, format à analyser
- **Besoin**: 
  - Capturer changements de couleur de fond
  - Capturer changements de texte
  - Identifier offset de la couleur RGB
  - Identifier offset et format du texte
- **Prochaine étape**: Captures avec différentes couleurs/textes

#### 2. ❌ Affichage d'Images Statiques
- **Commande**: Inconnue
- **Status**: Non identifiée
- **Besoin**: Capturer envoi d'image depuis SAMA
- **Format probable**: RGB565 ou PNG/JPG encodé

#### 3. ❌ Lecture de Vidéos (depuis fichier)
- **Commande**: 0x6e (set path) + 0x78 (play)
- **Status**: Protocole identifié mais non testé
- **Limitation**: Nécessite accès au filesystem du LCD
- **Note**: Le LCD a un système de fichiers interne (/tmp, /root, /mnt/SDCARD)

### Priorité MOYENNE

#### 4. ❌ Affichage de Données de Monitoring
- **Type**: CPU temp, GPU temp, RAM, etc.
- **Commande**: Probablement variante de 0xc8 ou nouveau packet
- **Status**: Non identifié
- **Besoin**: Capturer affichage de monitoring dans SAMA

#### 5. ❌ Graphiques / Jauges
- **Type**: Barres, cercles, graphiques
- **Commande**: Inconnue
- **Status**: Non identifié
- **Besoin**: Capturer affichage de widgets dans SAMA

#### 6. ❌ Animations
- **Type**: Transitions, effets
- **Commande**: Inconnue
- **Status**: Non identifié

### Priorité BASSE

#### 7. ❌ Upload de Fichiers vers le LCD
- **Type**: Images, vidéos, fonts
- **Commande**: Inconnue
- **Status**: Non identifié
- **Note**: Le LCD semble avoir un stockage interne

#### 8. ❌ Configuration Avancée
- **Type**: Rotation, calibration, etc.
- **Commande**: Inconnue
- **Status**: Non identifié

---

## 🔍 HYPOTHÈSES ET OBSERVATIONS

### Réponses du LCD
Le LCD envoie des réponses en **format texte** (UTF-8), pas en binaire:
- `"chs_5inch.dev1_rom1.89"` - ID du device
- `"media_stop"` - État de lecture média
- `"play_video_success"` - Confirmation lecture vidéo
- `"2688-1420-1268-..."` - Données de monitoring (?)

### Système de Fichiers Interne
Le LCD semble avoir un OS Linux embarqué avec:
- `/tmp/video/` - Stockage temporaire
- `/root/video/` - Stockage utilisateur
- `/mnt/SDCARD/video/` - Carte SD (si présente)

### Format de Données
- **Brightness**: 1 byte (0x00-0xFF)
- **Texte**: String UTF-8 terminée par 0x00
- **Couleur**: Probablement RGB888 (3 bytes) ou RGB565 (2 bytes)
- **Chemins**: String UTF-8 avec path absolu

### Padding
- Tous les packets sont **paddés à 250 bytes** avec 0x00
- Le padding commence après les données utiles

---

## 🛠️ OUTILS ET MÉTHODES

### Capture USB
- **Windows**: Wireshark + USBPcap
- **Filtres**: `usb.device_address == 21`
- **Endpoints surveillés**: 0x03 (OUT), 0x82 (IN)

### Analyse Serial
- **Outil**: Free Serial Port Monitor
- **Ports**: COM3 (init), COM4 (données)
- **Baud**: 115200

### Driver Python
- **Bibliothèque**: `pyserial`
- **Port**: COM4 (Windows) / /dev/ttyACM0 (Linux)
- **Fichiers**:
  - `sama_sm360_serial.py` - Driver principal
  - `test_brightness.py` - Test luminosité

---

## 📝 PROCHAINES ÉTAPES

### Immédiat
1. ✅ ~~Tester contrôle brightness~~ **FAIT**
2. ⚠️ **Analyser structure de la commande 0xc8** (fond + texte)
   - Capturer avec différentes couleurs
   - Capturer avec différents textes
   - Identifier offsets RGB et texte
3. ⚠️ Implémenter affichage texte/fond uni

### Court terme
4. ❌ Identifier commande pour images statiques
5. ❌ Identifier format de données de monitoring
6. ❌ Tester lecture vidéo (0x6e + 0x78)

### Moyen terme
7. ❌ Créer une API Python complète
8. ❌ Créer des exemples d'utilisation
9. ❌ Documenter toutes les commandes

### Long terme
10. ❌ Créer un daemon Linux
11. ❌ Intégration avec sensors Linux (lm-sensors, nvidia-smi)
12. ❌ Interface web de configuration

---

## 📚 RÉFÉRENCES

### Fichiers du Projet
```
sama_sm360/
├── captures/
│   ├── ini.txt                          # Première capture d'init
│   ├── ini_prise_2.txt                  # Init avec vidéo
│   ├── ini_sans_image_afficher.txt      # Init sans média
│   └── ini_avec_background_uni_text.txt # Fond uni + texte ⭐
├── drivers/
│   ├── sama_sm360_serial.py             # Driver principal
│   └── test_brightness.py               # Test luminosité
├── docs/
│   └── DISCOVERIES.md                   # Ce fichier
└── README.md
```


## 🎯 OBJECTIF FINAL

Créer un **driver Linux complet** permettant de:
- ✅ Contrôler la luminosité
- ⚠️ Afficher du texte personnalisé
- ❌ Afficher des images
- ❌ Afficher des données de monitoring système (CPU, GPU, RAM, etc.)
- ❌ Afficher des graphiques/jauges
- ❌ Lire des vidéos
- ❌ Configuration complète via CLI ou interface web

---

## 👥 CONTRIBUTIONS

**Auteur**: Simon DC alias : ScreeM
**Matériel**: Sama SM360 LCD AIO 5"
**Date début**: Janvier 2026

---

**Dernière mise à jour**: 16 janvier 2026
**Version du firmware**: dev1_rom1.89
**Status global**: 🟡 En développement actif (20% complété)
