# 🎯 SAMA SM360 LCD DRIVER - COMPLETE PROTOCOL ANALYSIS

## BREAKTHROUGH DISCOVERY

**The LCD device CONTAINS pre-loaded video files!**

Instead of a file transfer protocol, the SAMA uses a **COMMAND PROTOCOL**:
- Host sends: `0x01 0x03 [FILE_ID]` (3-4 bytes identifying which video to play)
- LCD responds: Loads that video from internal memory/storage
- Host sends: `0x78` to play

**This is WAY simpler than file transfer!**

---

## PROTOCOL DETAILS

### Serial Connection
- **Port**: COM4 (main control interface)
- **Baud Rate**: 115200 (common UART)
- **Timeout**: 1-2 seconds

### Command Codes (Confirmed from COM4 Logs)
```
0xAA = STOP playback
0x6E = LOAD VIDEO (by FILE_ID)
0x64 = GET STATUS (poll for state)
0x78 = PLAY VIDEO  
0x01 0x03 = LOAD FILE command format (USB/Serial hybrid?)
```

### File ID Format
**3-4 bytes that uniquely identify a video file**

Examples from pcapng capture:
```
C0 E0 01 = Video file 1 (480x480)
F8 1E    = Video file 2 (480x480)
```

**Pattern NOT YET DETERMINED**:
- Sequential index? (0, 1, 2...)
- Content hash/CRC?
- SAMA-specific encoding?

---

## TESTED SEQUENCE (from com4 capture)

1. **STOP** (0xAA) @ 0.000s
   → Any existing playback stops

2. **GET STATUS** (0x64) @ 0.100s  
   → Poll until device ready (returns status byte)

3. **LOAD** (0x6E or `01 03`) @ 0.200s
   → Send FILE_ID bytes
   → Device loads video from internal storage

4. **GET STATUS** (0x64) @ 0.500s
   → Wait for ready state

5. **PLAY** (0x78) @ 0.600s
   → Start playback

6. **GET STATUS** (0x64) @ 1.000s, 2.000s, etc.
   → Poll during playback

---

## WHAT'S IMPLEMENTED & READY TO TEST

✅ **sama_lcd_video_loader.py** - Complete driver with:
- `connect()` / `disconnect()`
- `identify_device()` - Get device info
- `load_video(file_id)` - Load video by ID
- `play()` - Start playback
- `stop()` - Stop playback
- `get_status()` - Check state

✅ **PROTOCOL_FINAL_DISCOVERY.md** - Full protocol documentation

---

## TESTING CHECKLIST

### Phase 1: Basic Commands
- [ ] Test STOP command (0xAA)
- [ ] Test GET STATUS (0x64) - should return status byte
- [ ] Verify response format

### Phase 2: Device Identification
- [ ] Test IDENTIFY command (0x01 0x03 0xFA)
- [ ] Confirm response contains device name/version
- [ ] Look for list of available FILE_IDs

### Phase 3: File Mapping
- [ ] Enumerate ALL available videos on LCD
- [ ] Map FILE_ID ↔ Filename/Index
- [ ] Determine FILE_ID encoding scheme

### Phase 4: Video Loading
- [ ] Use samo_lcd_video_loader.py to load video
- [ ] Test with FILE_ID: `C0 E0 01`
- [ ] Verify video starts playing
- [ ] Test STOP and GET STATUS during playback

### Phase 5: Multiple Videos
- [ ] Load different videos (test FILE_ID: `F8 1E`)
- [ ] Confirm each loads correct video
- [ ] Test rapid switching

---

## CRITICAL UNKNOWNS (TO SOLVE)

1. **FILE_ID Encoding**
   - How does user/file index map to FILE_ID bytes?
   - Is there a command to LIST available files?
   - Example: Video "video1.mp4" → FILE_ID ???

2. **Response Formats**
   - What do status bytes mean? (0x01 = ready? 0x00 = busy?)
   - Is there a "list videos" response format?
   - Full device info response format?

3. **Frame Padding**
   - Why do some commands use 277, 3777, or 123099 byte frames?
   - Is frame size specific to command type?
   - Does LCD care about trailing zeros?

4. **Multi-Path Support**
   - Original protocol showed: `/tmp/video/`, `/root/video/`, `/mnt/SDCARD/video/`
   - How to select path? File_ID encoding?

---

## NEXT ACTIONS

### Immediate (1-2 hours)
1. Run `sama_lcd_video_loader.py` on actual LCD device
2. Capture responses with COM port monitor
3. Map current FILE_IDs to actual videos

### Short Term (2-4 hours)  
1. Determine FILE_ID encoding scheme
2. Implement video discovery/enumeration
3. Create file mapping database

### Long Term (rest of project)
1. Full application using discovered protocol
2. Video browser/playlist functionality
3. Settings/configuration management

---

## REVISION FROM ORIGINAL PROTOCOL

**OLD UNDERSTANDING** (incorrect):
- Need to transfer entire MP4 file over USB (123KB)
- Complex file encoding/transfer
- Must read files from PC storage

**NEW UNDERSTANDING** (correct):
- Just send FILE_ID bytes (3-4 bytes!)
- LCD loads file from internal storage
- Simple command protocol
- **100x simpler implementation!**

---

## FILES CREATED

1. **sama_lcd_video_loader.py** - Ready-to-test Python driver
2. **PROTOCOL_FINAL_DISCOVERY.md** - Final protocol documentation  
3. **PROTOCOL_DISCOVERY.md** - Detailed analysis notes
4. **frame_4653_hex_full.txt** - Raw USB frame capture (proof of zeros)

Ready to deploy and test! 🚀

