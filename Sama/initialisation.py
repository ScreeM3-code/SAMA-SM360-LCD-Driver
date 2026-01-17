def initialize_sama_sm360(dev):
    """Séquence complète d'init basée sur le sniff"""

    # 1. Handshake initial (BULK)
    handshake = bytes.fromhex("""
        1b 00 10 50 00 00 00 00 ff ff 00 00 00 00 09 00
        00 02 00 0a 00 81 03 00 00 00 00
    """.replace('\n', '').replace(' ', ''))
    dev.write(0x01, handshake)
    time.sleep(0.1)

    # 2. Setup interrupt (INTERRUPT)
    interrupt_setup = bytes.fromhex("""
        1b 00 10 60 00 00 00 00 ff ff 00 00 00 00 09 00
        00 02 00 0a 00 84 01 00 00 00 00
    """.replace('\n', '').replace(' ', ''))
    # Note: INTERRUPT endpoint might be auto-handled

    # 3. HID GET_REPORT (CONTROL IN)
    # bmRequestType=0xa1, bRequest=0x21
    response = dev.ctrl_transfer(
        bmRequestType=0xa1,  # IN, Class, Interface
        bRequest=0x21,  # GET_REPORT
        wValue=0x0800,  # Report Type & ID
        wIndex=0x0000,  # Interface
        data_or_wLength=8
    )
    time.sleep(0.05)

    # 4. Main init command (CONTROL OUT) - répété 2x
    init_cmd = bytes.fromhex("""
        01 02 00 0a 00 80 02 07 00 00 00 03 00 c2 01 00
        00 00 08
    """.replace('\n', '').replace(' ', ''))

    for _ in range(2):
        dev.ctrl_transfer(
            bmRequestType=0x21,  # OUT, Class, Interface
            bRequest=0x09,  # SET_REPORT
            wValue=0x0200,
            wIndex=0x0000,
            data_or_wLength=init_cmd
        )

        # Read status entre les deux
        dev.ctrl_transfer(
            bmRequestType=0xa1,
            bRequest=0x21,
            wValue=0x0800,
            wIndex=0x0000,
            data_or_wLength=8
        )
        time.sleep(0.05)

    # 5. Confirmation (BULK avec flag 01 c0)
    confirm = bytes.fromhex("""
        1b 00 10 50 00 00 00 00 ff ff 00 00 01 c0 09 00
        01 02 00 0a 00 81 03 00 00 00 00
    """.replace('\n', '').replace(' ', ''))
    dev.write(0x01, confirm)
    time.sleep(0.1)

    # 6. HID SET_REPORT final
    dev.ctrl_transfer(
        bmRequestType=0x21,
        bRequest=0x09,
        wValue=0x0222,
        wIndex=0x0000,
        data_or_wLength=bytes.fromhex("00 02 00 0a 00 00 02 08 00 00 00 00")
    )

    # 7. Init finale
    dev.ctrl_transfer(
        bmRequestType=0x21,
        bRequest=0x09,
        wValue=0x0200,
        wIndex=0x0000,
        data_or_wLength=bytes.fromhex("01 02 00 0a 00 00 02 00 00 00 00 03")
    )

    # 8. Final handshake
    dev.write(0x01, handshake)  # Même que #1

    print("✅ Sama SM360 initialized!")
