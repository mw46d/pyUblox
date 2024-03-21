#! /usr/bin/env python

import ublox
import sys

from pylab import *

dev = ublox.UBlox(sys.argv[1])
dev.configure_ublox_usb_sat(True)

raw = []
svi = []
pos = []
sat = []

while True:
    msg = dev.receive_message()

    if msg is None:
        break

    n = msg.name()
    print(n)

    if n not in ['RXM_RAW', 'NAV_SVINFO', 'NAV_SAT']:
        continue

    msg.unpack()

    if n == 'RXM_RAW':
        raw.append(msg.numSV)
    elif n == 'NAV_SVINFO':
        svi.append(msg.numCh)

        # count how many of the active channels are used in the pos solution
        c = 0
        for s in msg.recs:
            if s.flags & 1:
                c += 1

        pos.append(c)
    elif n == 'NAV_SAT':
        sat.append(msg.numSvs)

        c = 0
        for s in msg.recs:
            if s.flags & 0x08 == 0x08:
                c += 1
        pos.append(c)
        print('Sats: %d, Used: %d' % (msg.numSvs, c))

plot(raw, label="Raw")
plot(svi, label="SVI")
plot(pos, label="Pos")
legend()
show()
