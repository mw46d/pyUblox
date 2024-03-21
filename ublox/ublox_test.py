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
    dev.configure_ublox_usb_out(True)
    dev.configure_ublox_usb_sat(True)
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
            dev.configure_ublox_usb_out(False)
            time.sleep(20)
            dev.configure_ublox_usb_out(True)
    print("tested %u messages OK" % count)
