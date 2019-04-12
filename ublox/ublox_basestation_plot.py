#!/usr/bin/env python

import ublox, sys, fnmatch, os, time
import RTCMv3_decode
import numpy, util, math
from collections import deque
import matplotlib
from matplotlib import pyplot
from matplotlib.lines import Line2D
import matplotlib.animation as animation

from optparse import OptionParser

parser = OptionParser("ublox_basestation_plot.py [options] <device_file>")
parser.add_option("--ntrip-server", default = 'tiburon.geo.berkeley.edu')
parser.add_option("--ntrip-port", type = 'int', default = 2101)
parser.add_option("--ntrip-user")
parser.add_option("--ntrip-password")
parser.add_option("--ntrip-mount", default = 'DIAB_RTCM3')

(opts, args) = parser.parse_args()

# create a figure
f = pyplot.figure(1)
f.clf()
ax1 = f.add_axes([ 0.05, 0.05, 0.9, 0.9])

for d in args:
    dev = ublox.UBlox(d)

def send_rtcm(msg):
    # print(msg)
    dev.write(msg)

rtcm_thread = RTCMv3_decode.run_RTCM_converter(opts.ntrip_server, opts.ntrip_port, opts.ntrip_user,
    opts.ntrip_password, opts.ntrip_mount, rtcm_callback = send_rtcm)

def get_xy(pos, home):
    distance = util.gps_distance(home[0], home[1], pos[0], pos[1])
    bearing = util.gps_bearing(home[0], home[1], pos[0], pos[1])
    x = distance * math.sin(math.radians(bearing))
    y = distance * math.cos(math.radians(bearing))
    return (x,y)

def plot_line(pos1, pos2, home, colour):
    global ax1
    (x1,y1) = get_xy(pos1, home)
    (x2,y2) = get_xy(pos2, home)
    ax1.plot([x1,x2], [y1,y2], colour, linestyle='solid', marker=None, alpha=0.5)

pos_d = deque([], 1200)
satcount_string = ''
status_string = ''
svin_string = ''

def animate(i):
    global ax1
    global dev
    global pos_d
    global rtcm_thread
    global satcount_string
    global status_string
    global svin_string

    msg = dev.receive_message(ignore_eof = True)
    msg.unpack()
    # print msg.name()
    if msg.name() == 'NAV_POSLLH':
        pos = (msg.Latitude * 1.0e-7, msg.Longitude * 1.0e-7)
        pos_d.appendleft(pos)
        ax1.clear()
        d_home = pos_d[0]
        d_p1 = d_home
        for d_p2 in pos_d:
            if util.gps_distance(d_home[0], d_home[1], d_p2[0], d_p2[1]) < 5:
                plot_line(d_p1, d_p2, d_home, 'ro')
                d_p1 = d_p2
        ax1.text(0.99, 0.62, "\n".join([ "%.8f, %.8f" % (pos_d[0]), status_string, satcount_string, svin_string ]),
            horizontalalignment='right',
            verticalalignment='bottom',
            transform=ax1.transAxes)

    elif msg.name() == 'NAV_SAT':
        c = 0
        for s in msg.recs:
            if s.flags & 0x08 == 0x08:
                c += 1
        satcount_string = "Sats:  %d(%d)" % (c, msg.numSvs)
    elif msg.name() == 'NAV_SVIN':
        svin_string = "Survey In:\n"
        svin_string += "Duration: %d s\n" % msg.dur
        svin_string += "Accuracy: %.4f m\n" % (msg.meanAcc * 0.0001)
        svin_string += "Observts: %d\n" % msg.obs
        svin_string += "Valid:    %s\n" % str(msg.isvalid)
        svin_string += "Active:   %s" % str(msg.active)
    elif msg.name() == 'NAV_STATUS':
        f = '-'
        if msg.flags & 0x01 == 0x01:
            if msg.gpsFix == 2:
                f = "2D"
            elif msg.gpsFix == 3:
                f = "3D"
            elif msg.gpsFix == 5:
                f = "TIME"
                if rtcm_thread is not None:
                    rtcm_thread.join(60)
                    rtcm_thread = None
        if msg.flags & 0x02 == 0x02:
            f += '/DIFF'
        status_string = "Status: " + f
        print("flags= %02x %02x" % (msg.flags, msg.fixStat))

ani = animation.FuncAnimation(f, animate)
pyplot.show()
raw_input('Press enter')

