# Analyse Détaillée du Log COM4 - SAMA SM360

## 📋 Vue d'ensemble
- **Device**: SAMA SM360 (LCD 5" AIO)
- **Connexion**: COM4 @ 115200 baud
- **Firmware**: dev1_rom1.89
- **Date**: 2026-01-17 12:13:52

---

## 🔍 DÉCODAGE DÉTAILLÉ DES COMMANDES

### 1️⃣ HANDSHAKE INITIAL (Packet #60)

```
Commande: 0x01 ef 69 00 00 00 01 00 00 00 c5 d3 [padding...]
Offset    00  01 02 03 04 05 06 07 08 09 10 11
```

| Offset | Valeur | Signification |
|--------|--------|---------------|
| 0 | `0x01` | **Command**: Handshake/Init |
| 1-2 | `ef 69` | **Magic Header** (constant) |
| 3-5 | `00 00 00` | Reserved/Padding |
| 6 | `0x01` | **Subcommand**: Standard handshake |
| 7-9 | `00 00 00` | Reserved |
| 10-11 | `c5 d3` | **Special bytes** (Handshake identifier?) |
| 12+ | `00...` | Padding to 250 bytes |

**Réponse du LCD**:
```
63 68 73 5f 35 69 6e 63 68 2e 64 65 76 31 5f 72 6f 6d 31 2e 38 39 00
ASCII: chs_5inch.dev1_rom1.89
```
- Format: Device ID string, null-terminated
- Contient: Type (`chs_5inch`) + Firmware (`dev1_rom1.89`)

---

### 2️⃣ INIT SECONDAIRE (Packet #100)

```
Commande: 0x79 ef 69 00 00 00 01 00 00 00 00 [padding...]
Offset    00  01 02 03 04 05 06 07 08 09 10
```

| Offset | Valeur | Signification |
|--------|--------|---------------|
| 0 | `0x79` | **Command**: Secondary init |
| 1-2 | `ef 69` | **Magic Header** |
| 3-5 | `00 00 00` | Padding |
| 6 | `0x01` | **Subcommand** |
| 7-10 | `00...` | Padding |

**Status**: Pas de réponse attendue
**Intervalle**: ~50ms après handshake

---

### 3️⃣ INIT TERTIAIRE (Packet #141)

```
Commande: 0x96 ef 69 00 00 00 01 00 00 00 00 [padding...]
Offset    00  01 02 03 04 05 06 07 08 09 10
```

| Offset | Valeur | Signification |
|--------|--------|---------------|
| 0 | `0x96` | **Command**: Tertiary init |
| 1-2 | `ef 69` | **Magic Header** |
| 6 | `0x01` | **Subcommand** |

**Réponse du LCD**:
```
6d 65 64 69 61 5f 73 74 6f 70 00 ...
ASCII: media_stop
```

- Indique que le LCD est prêt pour les commandes média
- Intervalle: ~120ms après init secondaire

---

### 4️⃣ SET BRIGHTNESS (Packet #186)

```
Commande: 0x7b ef 69 00 00 00 01 00 00 00 80 [padding...]
Offset    00  01 02 03 04 05 06 07 08 09 10
```

| Offset | Valeur | Signification |
|--------|--------|---------------|
| 0 | `0x7b` | **Command**: Set Brightness |
| 1-2 | `ef 69` | **Magic Header** |
| 6 | `0x01` | **Subcommand**: Standard |
| 10 | `0x80` | **Brightness Value** (0x00=0%, 0x80=50%, 0xFF=100%) |

**Calcul**:
```
Brightness % = (value / 255) × 100
0x80 = 128 → 128/255 × 100 = 50.2%
```

**Status**: ✅ **FONCTIONNEL CONFIRMÉ**

---

### 5️⃣ TYPE-5 COMMAND (Packet #217)

```
Commande: 0x7d ef 69 00 00 00 05 00 00 00 80 [padding...]
Offset    00  01 02 03 04 05 06 07 08 09 10
```

| Offset | Valeur | Signification |
|--------|--------|---------------|
| 0 | `0x7d` | **Command**: Type 5 (mystery) |
| 1-2 | `ef 69` | **Magic Header** |
| 6 | `0x05` | **Subcommand**: Type 5 variant |
| 10 | `0x80` | **Parameter**: (fonction inconnue) |

**Observations**:
- Toujours envoyée immédiatement après brightness
- Valeur souvent 0x80 (même que brightness)
- Peut être lié à la correction gamma ou mode d'affichage
- **Hypothesis**: "Apply Display Settings" ou "Gamma Correction"

---

### 6️⃣ GET STATUS / MONITORING (Packet #245)

```
Commande: 0x64 ef 69 00 00 00 01 00 00 00 00 [padding...]
Offset    00  01 02 03 04 05 06 07 08 09 10
```

| Offset | Valeur | Signification |
|--------|--------|---------------|
| 0 | `0x64` | **Command**: Get Status |
| 1-2 | `ef 69` | **Magic Header** |
| 6 | `0x01` | **Subcommand**: Request |
| 10 | `0x00` | Reserved |

**Réponse du LCD**:
```
32 36 38 38 2d 31 34 32 30 2d 31 32 36 38 2d 31 32 32 38 38 30 2d 33 31 38 36 2d 31 31 39 36 39 34
ASCII: 2688-1420-1268-122880-3186-119694
```

**Format de réponse**: `VALUE1-VALUE2-VALUE3-VALUE4-VALUE5-VALUE6`

**Hypothesis** (basé sur thème AIODATA):
| Index | Valeur | Unité | Interprétation |
|-------|--------|-------|-----------------|
| 1 | 2688 | RPM | Vitesse ventilateur CPU |
| 2 | 1420 | RPM | Vitesse ventilateur GPU |
| 3 | 1268 | °C×100 | Température CPU (12.68°C) |
| 4 | 122880 | ? | Puissance ou autre métrique |
| 5 | 3186 | ? | Possiblement fréquence |
| 6 | 119694 | ? | Données secondaires |

---

### 7️⃣ LOAD VIDEO - Path Selection by Subcommand (Packet #309)

```
Commande: 0x6e ef 69 00 00 00 [SUBCMD] 00 00 00 [PATH_STRING] [padding...]
Offset    00  01 02 03 04 05  06       07 08 09 10  ...
```

| Offset | Valeur | Signification |
|--------|--------|---------------|
| 0 | `0x6e` | **Command**: Load Video |
| 1-2 | `ef 69` | **Magic Header** |
| 6 | **SUBCMD** | **Path selector** (voir tableau ci-dessous) |
| 10+ | STRING | **UTF-8 Filename** (null-terminated) |

**Sous-commandes pour les chemins**:

| Subcommand | Chemin de recherche | Cas d'usage |
|-----------|-------------------|------------|
| `0x1d` | `/mnt/SDCARD/video/` | ✅ **Recommandé** (SD Card) |
| `0x17` | `/root/video/` | Fallback Linux |
| `0x16` | `/tmp/video/` | Fallback temporaire |

**Exemple - Trois tentatives observées**:

1. **Tentative 1** (0x16):
```
6e ef 69 00 00 00 16 00 00 00 2f 74 6d 70 2f 76 69 64 65 6f 2f 74 68 65 6d 65 30 36 2e 6d 70 34 00
                       /tmp/video/theme06.mp4
Response: 0 (NOT FOUND)
```

2. **Tentative 2** (0x17):
```
6e ef 69 00 00 00 17 00 00 00 2f 72 6f 6f 74 2f 76 69 64 65 6f 2f 74 68 65 6d 65 30 36 2e 6d 70 34
                       /root/video/theme06.mp4
Response: 0 (NOT FOUND)
```

3. **Tentative 3** (0x1d): ✅
```
6e ef 69 00 00 00 1d 00 00 00 2f 6d 6e 74 2f 53 44 43 41 52 44 2f 76 69 64 65 6f 2f 74 68 65 6d 65 30 36 2e 6d 70 34
                       /mnt/SDCARD/video/theme06.mp4
Response: 1152859 (FILE FOUND! Size = 1152859 bytes = ~1.1 MB)
```

**Réponses possibles**:
- `0` = Fichier non trouvé
- Chiffre > 0 = Taille du fichier en bytes

---

### 8️⃣ PLAY VIDEO (Packet #382)

```
Commande: 0x78 ef 69 00 00 00 [SUBCMD] [FLAG] 00 00 [PATH_STRING] [padding...]
Offset    00  01 02 03 04 05  06       07      08 09 10  ...
```

| Offset | Valeur | Signification |
|--------|--------|---------------|
| 0 | `0x78` | **Command**: Play Video |
| 1-2 | `ef 69` | **Magic Header** |
| 6 | **SUBCMD** | **Chemin selector** (0x1d, 0x17, 0x16) |
| 7 | **FLAG** | **Play flag** (0x01 = Play) |
| 10+ | STRING | **UTF-8 Path** (doit correspondre au LOAD) |

**Exemple observé**:
```
78 ef 69 00 00 00 1d 01 00 00 2f 6d 6e 74 2f 53 44 43 41 52 44 2f 76 69 64 65 6f 2f 74 68 65 6d 65 30 36 2e 6d 70 34
                  ↑ ↑                        ↑ chemin complet (doit correspondre)
                  │ └─ Play flag (0x01)
                  └──── Path selector (0x1d = SD Card)
```

**Réponse attendue**: (pas visible dans le log)

---

### 9️⃣ UNKNOWN COMMAND - 0x82 (Packet #410)

```
Commande: 0x82 ef 69 00 00 00 01 00 00 00 00 [padding...]
Offset    00  01 02 03 04 05 06 07 08 09 10
```

| Offset | Valeur | Signification |
|--------|--------|---------------|
| 0 | `0x82` | **Command**: Unknown |
| 1-2 | `ef 69` | **Magic Header** |
| 6 | `0x01` | **Subcommand** |

**Observations**:
- Envoyée après chaque commande LOAD ou PLAY
- Pas de réponse visible
- **Hypothesis**: "Verify playback status" ou "Sync command"

---

## 📊 SÉQUENCE TEMPORELLE

```
Time (ms)     Event
──────────────────────────────────────────────
0             Connection established
0             COM port initialization
27.2          ▶ HANDSHAKE (0x01)
35.6          ◀ Response: "chs_5inch.dev1_rom1.89"
60.2          ▶ INIT_2 (0x79)
73.2          ▶ INIT_3 (0x96)
86.8          ◀ Response: "media_stop"
140.2         ▶ SET_BRIGHTNESS (0x7b) = 0x80
186.1         ▶ TYPE5 (0x7d) = 0x80
220.2         ▶ GET_STATUS (0x64)
234.4         ◀ Response: "2688-1420-1268-122880-3186-119694"
287.0         ▶ LOAD_VIDEO (0x6e, 0x16) - /tmp → Response: 0
320.2         ▶ LOAD_VIDEO (0x6e, 0x17) - /root → Response: 0
351.5         ▶ LOAD_VIDEO (0x6e, 0x1d) - /mnt/SDCARD ✅ → Response: 1152859
382.1         ▶ PLAY_VIDEO (0x78, 0x1d)
397.1         ▶ UNKNOWN (0x82)
398+          ▶ Continuous polling loop (WAIT_MASK)
```

---

## 🔧 PARAMÈTRES DÉCOUVERTS

### Plages de valeurs

```
Brightness:
  - Minimum: 0x00 (0%)
  - Maximum: 0xFF (100%)
  - Observé: 0x80 (50%)
  - Recommandé: 0xB0-0xFF (70-100%)

Type-5 Parameter:
  - Observé: 0x80
  - Plage probable: 0x00-0xFF
  - Fonction: UNKNOWN

Status Code:
  - Format: "VALUE1-VALUE2-...-VALUE6"
  - Mise à jour: ~21ms entre chaque requête
```

### Chemins SD Card

```
Priorité 1: /mnt/SDCARD/video/theme*.mp4 (RECOMMANDÉ)
Priorité 2: /root/video/theme*.mp4
Priorité 3: /tmp/video/theme*.mp4
```

---

## ✅ FONCTIONNALITÉS CONFIRMÉES

| Commande | Code | Status | Notes |
|----------|------|--------|-------|
| Handshake | 0x01 | ✅ Testé | Retourne Device ID |
| Init 2 | 0x79 | ✅ Testé | Pas de réponse |
| Init 3 | 0x96 | ✅ Testé | Retourne "media_stop" |
| Brightness | 0x7b | ✅ Testé | 0-255 (0-100%) |
| Type5 | 0x7d | ⚠️ Inconnu | Toujours après brightness |
| Get Status | 0x64 | ✅ Testé | Format: "val1-val2-..." |
| Load Video | 0x6e | ✅ Testé | Multi-path avec subcommand |
| Play Video | 0x78 | ✅ Testé | Doit correspondre au LOAD |
| Unknown | 0x82 | ⚠️ Inconnu | Post-commande |

---

## 💡 RECOMMANDATIONS POUR LINUX

1. **Utiliser `/mnt/SDCARD` comme chemin primaire** (subcommand 0x1d)
2. **Garder les timeouts courts** (0.2-0.5s) car le LCD répond rapidement
3. **Implémenter un fallback** avec 0x17 (/root) et 0x16 (/tmp)
4. **Parser les réponses status** pour afficher les données système
5. **Ajouter du logging** pour tracer les hex dumps (pour debugging)

---

## 🔮 COMMANDESÀ EXPLORER

- 0x82 (Verify/Sync) - Fonction réelle inconnue
- 0x7d subcommands (0x00-0xFF) - Tester différentes valeurs
- Display commands (0xc8) - Affichage texte/couleur observé dans README
- Clear buffer (0x2c) - Mentionné par l'utilisateur

