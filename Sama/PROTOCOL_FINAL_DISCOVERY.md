# 🎯 FINAL PROTOCOL DISCOVERY - FILE LOADING MECHANISM

## KEY FINDING

**Le LCD contient DÉJÀ les fichiers vidéo en mémoire!**  
Le protocole USB n'envoie PAS les fichiers vidéo bruts, mais plutôt des **COMMANDES** avec **FILE IDs**.

---

## PROTOCOL STRUCTURE

### Command Format
```
USB Frame Structure:
  [USB Header: 1b 00 ... (16 bytes)]
  [Endpoint Info: 00 02 00 0b 00]
  [COMMAND CODE: 01 03]
  [FILE ID: variable bytes (3-4 bytes)]
  [PADDING: zeros to fill frame size]

Total Frame Size: variable (277 bytes, 3777 bytes, 123099 bytes, etc.)
```

### Commands Identified

**Command: `01 03 FA ...`** (277 bytes)
- Purpose: Device identification/initialization
- Response: Device info string `"chs_5inch.dev1_rom1.89"`

**Commands: `01 03 [FILE_ID] ...`** (large frames: 3777, 123099 bytes)
- Purpose: Load video file
- FILE_ID: 3-4 bytes that uniquely identify a video file
- Frame filled with zeros (padding)

---

## FILE ID EXAMPLES (from usb run2.pcapng)

| Frame | Time (s) | Size (bytes) | FILE ID (hex) | Status |
|-------|----------|-------------|---------------|--------|
| 4653  | 9.786481 | 123099 | `C0 E0 01` | Video file 1 |
| 4841  | 9.867146 | 123171 | `F8 1E` | Video file 2 |

---

## IMPLICATIONS FOR PYTHON IMPLEMENTATION

### What we DON'T need to do:
- ❌ Read video files from PC
- ❌ Compress/encode video files  
- ❌ Send large file data over USB

### What we NEED to do:
- ✅ Discover the FILE ID mapping
- ✅ Send command: `01 03 [FILE_ID]` with proper frame padding
- ✅ Wait for ACK/response

### CRITICAL QUESTION:
**How are FILE IDs determined?**

Possible approaches:
1. **Index-based**: FILE_ID = video file index on LCD (0, 1, 2, 3...)
2. **Content-hash based**: FILE_ID = CRC32 or hash of filename
3. **Enumeration**: Use device identification command to get list of available files
4. **SAMA-specific**: Proprietary ID scheme based on directory/filename

---

## NEXT STEPS

1. **Analyze all transfers in usb run2.pcapng** to map FILE IDs
2. **Identify the pattern** (sequential, hash-based, enumeration?)
3. **Test hypothesis** by trying different FILE IDs
4. **Document FILE ID scheme** for 480x480 resolution
5. **Implement in Python** using pyserial (COM4)

---

## REVISED VIDEO_PLAYER PROTOCOL

Instead of:
```
1. Read MP4 file from PC
2. Open USB bulk endpoint  
3. Send 123KB of file data
4. Send PLAY command
```

Actually do:
```
1. Determine FILE_ID for desired video
2. Send command: 0x01 0x03 [FILE_ID]
3. Send PLAY command
```

**Much simpler!**

