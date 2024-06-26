#!/usr/bin/env python3
'''
test ublox parsing, packing and printing
'''
import fnmatch
import os
import sys
import time
import ublox

from optparse import OptionParser

parser = OptionParser("ublox_test.py [options] <file>")
parser.add_option("--baudrate", type='int',
                  help="serial baud rate", default=115200)
parser.add_option("-f", "--follow", action='store_true', default=False, help="ignore EOF")
parser.add_option("--show", action='store_true', default=False, help='show messages while capturing')

(opts, args) = parser.parse_args()

for f in args:
    print('Testing %s' % f)
    dev = ublox.UBlox(f, baudrate = opts.baudrate)
    if True:
        dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_UART1OUTPROT_UBX': True }]))
        dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_UART1OUTPROT_NMEA': False }]))
        dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_UBX_NAV_SAT_UART1': True }]))
        dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_UBX_NAV_POSLLH_UART1': True }]))
        dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_UBX_NAV_DOP_UART1': True }]))
    else:
        # Just a way to configure things
        dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_UART1OUTPROT_UBX': False }]))
        dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_UART1OUTPROT_NMEA': True }]))
        dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_NMEA_ID_GGA_UART1': 1 }]))
        dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_NMEA_ID_GST_UART1': 1 }]))
        dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_NMEA_ID_RMC_UART1': 1 }]))
        dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_NMEA_ID_VTG_UART1': 1 }]))

        dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_NMEA_ID_GLL_UART1': 0 }]))
        dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_NMEA_ID_GSA_UART1': 0 }]))
        dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_NMEA_ID_GSV_UART1': 0 }]))
        sys.exit(0)

    count = 0
    while True:
        msg = dev.receive_message(ignore_eof=opts.follow)
        if msg is None:
            break
        buf1 = msg._buf[:]
        msg.unpack()
        s1 = str(msg)
        msg.pack()
        msg.unpack()
        s2 = str(msg)
        buf2 = msg._buf[:]
        if buf1 != buf2:
            print("repack failed")
            break
        if s1 != s2:
            print("repack string failed")
            break
        if opts.show:
            print(s1)
        count += 1
        if count == 100:
            dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_UART1OUTPROT_UBX': False }]))
            time.sleep(20)
            dev.configure_ublox_kv(ublox.UbloxConfigKV.pack([{ 'CFG_UART1OUTPROT_UBX': True }]))
            print("After reconfig")
    print("tested %u messages OK" % count)
