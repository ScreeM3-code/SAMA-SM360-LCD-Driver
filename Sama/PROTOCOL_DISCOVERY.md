# USB FILE TRANSFER PROTOCOL DÉCOUVERTE

## Résolution testée: 480x480  
## Fichier vidéo: ~123KB

---

## SÉQUENCE COMPLÈTE DE TRANSFERT

### Phase 1: Initialisation (Timestamp 6.817775s)
**Frame 3153 - URB_BULK out (277 bytes)**
```
Hex: 1b 00 10 50 7d ab 8a 80 ff ff 00 00 00 00 09 00
     00 02 00 0b 00 01 03 fa 00 00 00 01 ef 69 00 00
```
**Analyse**: 
- `1b 00` = En-tête USB
- `00 02 00 0b 00` = Information d'endpoint
- `01 03 fa` = **COMMANDE PRINCIPALE**
- Suivi de 16 bytes (paramètres)
- Reste: zeros de padding

**Réponse Frame 3167 (50 bytes) @ 6.855342s**:
```
Hex: 1b 00 b0 a2 69 a7 8a 80 ff ff 00 00 00 00 09 00
     01 02 00 0b 00 81 03 17 00 00 00 63 68 73 5f 35
     69 6e 63 68 2e 64 65 76 31 5f 72 6f 6d 31 2e 38
     39 00
Texte: "chs_5inch.dev1_rom1.89"
```
→ Réponse avec **VERSION DU DEVICE LCD**

---

### Phase 2: Sélection du fichier (Timestamps 9.785-9.786s)

**Frame 4647** @ 9.785703s - 277 bytes URB_BULK out
```
Hex: 01 03 fa 00 00 00 ca ef 69 00 0e 10 [padding...]
```
→ Commande de sélection/préparation

**Frame 4648** @ 9.785744s - 27 bytes URB_BULK out  
→ Status ou confirmation (très court)

**Frame 4649** @ 9.786147s - 3777 bytes URB_BULK out
```
Hex: 01 03 a6 0e 00 00 00 00 [3761 bytes de padding...]
```
→ **COMMANDE "PRÉPARE-TOI À RECEVOIR LE FICHIER"**

---

### Phase 3: TRANSFERT FICHIER VIDÉO

**Frame 4653** @ 9.786481s - **123099 bytes URB_BULK out**
```
Hex: 01 03 c0 e0 01 00 [123083 bytes de données vidéo...]
```

**Analyse du header**:
- `01 03` = Code de commande (constant dans tous les transferts)
- `c0 e0 01` = Identifiant ou paramètre du fichier (change per fichier)
- **Puis: DONNÉES VIDÉO BRUTES** (MP4 ou autre format)

---

## PROTOCOLE DÉCOUVERT

### Structure de commande générale:
```
[USB Header: 1b 00 ...]
[Endpoint info: 00 02 00 0b 00]
[COMMAND CODE: 01 03]
[COMMAND PARAMS: variable bytes]
[PADDING: zeros jusqu'à taille frame]
```

### Commandes identifiées:

1. **0x01 0x03 0xFA** = Commande d'information / identification
   - Retour: Version device

2. **0x01 0x03 0xA6 0x0E** = Préparation pour envoi de fichier
   - Suivi de 3777 bytes (probablement metadata)

3. **0x01 0x03 0xC0 0xE0 0x01** = Transfert de données
   - Puis 123083 bytes de fichier réel

---

## STATISTIQUES CAPTURE

| Frame | Time (s) | Size (bytes) | Direction | Status |
|-------|----------|-------------|-----------|--------|
| 3153  | 6.817775 | 277 | OUT | Initialization |
| 3167  | 6.855342 | 50  | IN  | Response: "chs_5inch..." |
| 4647  | 9.785703 | 277 | OUT | File selection |
| 4648  | 9.785744 | 27  | OUT | Confirmation |
| 4649  | 9.786147 | 3777| OUT | Prepare for file |
| 4653  | 9.786481 | 123099| OUT| **VIDEO FILE DATA** |

**Total File Transfer Time**: 9.786481 - 9.786147 = **0.334ms** (instant!)

---

## PROCHAINES ÉTAPES

1. Confirmer le format des bytes de commande (`01 03 XX XX`)
2. Tester avec différentes résolutions (480x480s, 480x480r, 720x720, etc.)
3. Identifier le protocole complet:
   - Quels chemins de destination? (`/tmp`, `/root`, `/mnt/SDCARD`?)
   - Comment encoder la metadata dans frame 4649?
   - Quel est le vrai format du fichier? (MP4 raw, compressed, etc?)
4. Implémenter en Python utilisant `pyusb` ou `pyserial` avec handle USB brut

