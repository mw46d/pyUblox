#!/usr/bin/env python3

import ublox, sys, fnmatch, os, time
import RTCMv3_decode
import numpy, util, math
from collections import deque
import datetime
import struct

have_display = 'DISPLAY' in os.environ

if have_display:
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

log_fd = open(os.path.expanduser("~/base_station_%s.log" % (datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S'))), "w")
log_fd.write("%s: New log\n" % (datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')))
log_fd.flush()

if have_display:
    # create a figure
    f = pyplot.figure(1)
    f.clf()
    ax1 = f.add_axes([ 0.05, 0.05, 0.9, 0.9])
else:
    # tty_fd = open('/dev/tty3', 'w+')
    tty_fd = open('/dev/tty3', 'w')

for d in args:
    dev = ublox.UBlox(d)

    # Test
    b = ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_UBX_NAV_HPPOSLLH_USB': 1 }])
    payload = struct.pack('<BBh', 0, 1, 0)
    payload += b
    dev.send_message(ublox.CLASS_CFG, ublox.MSG_CFG_VALSET, payload)

    b = ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_UBX_NAV_SAT_USB': 1 }])
    payload = struct.pack('<BBh', 0, 1, 0)
    payload += b
    dev.send_message(ublox.CLASS_CFG, ublox.MSG_CFG_VALSET, payload)

    b = ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_UBX_NAV_SVIN_USB': 1 }])
    payload = struct.pack('<BBh', 0, 1, 0)
    payload += b
    dev.send_message(ublox.CLASS_CFG, ublox.MSG_CFG_VALSET, payload)

    b = ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_UBX_NAV_STATUS_USB': 1 }])
    payload = struct.pack('<BBh', 0, 1, 0)
    payload += b
    dev.send_message(ublox.CLASS_CFG, ublox.MSG_CFG_VALSET, payload)

    b = ublox.UbloxConfigKV.pack([{ 'CFG_MSGOUT_UBX_NAV_PVT_USB': 1 }])
    payload = struct.pack('<BBh', 0, 1, 0)
    payload += b
    dev.send_message(ublox.CLASS_CFG, ublox.MSG_CFG_VALSET, payload)

    b = ublox.UbloxConfigKV.pack([{ 'CFG_TMODE_MODE': 0 }])
    payload = struct.pack('<BBh', 0, 1, 0)
    payload += b
    dev.send_message(ublox.CLASS_CFG, ublox.MSG_CFG_VALSET, payload)

    # base2 b = ublox.UbloxConfigKV.pack([{ 'CFG_TMODE_SVIN_MIN_DUR': 8 * 60 * 60 }]) # 8 h
    b = ublox.UbloxConfigKV.pack([{ 'CFG_TMODE_SVIN_MIN_DUR': 20 * 60 }]) # 20 minutes
    payload = struct.pack('<BBh', 0, 1, 0)
    payload += b
    dev.send_message(ublox.CLASS_CFG, ublox.MSG_CFG_VALSET, payload)

    # base2 b = ublox.UbloxConfigKV.pack([{ 'CFG_TMODE_SVIN_ACC_LIMIT': 100 * 10 }]) # 10 cm
    b = ublox.UbloxConfigKV.pack([{ 'CFG_TMODE_SVIN_ACC_LIMIT': 100 * 30 }]) # 30 cm
    payload = struct.pack('<BBh', 0, 1, 0)
    payload += b
    dev.send_message(ublox.CLASS_CFG, ublox.MSG_CFG_VALSET, payload)

    b = ublox.UbloxConfigKV.pack([{ 'CFG_TMODE_MODE': 1 }])
    payload = struct.pack('<BBh', 0, 1, 0)
    payload += b
    dev.send_message(ublox.CLASS_CFG, ublox.MSG_CFG_VALSET, payload)

def send_rtcm(msg):
    # print(msg)
    dev.write(msg)

rtcm_thread = RTCMv3_decode.run_RTCM_converter(opts.ntrip_server, opts.ntrip_port, opts.ntrip_user,
    opts.ntrip_password, opts.ntrip_mount, rtcm_callback = send_rtcm)
#rtcm_thread = None

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
status_age = None
svin_string = ''
diff_age_a = [ 'None', '0 - 1s', '1 - 2s', '2 - 5s',
               '5 - 10s', '10 -15s', '15 - 20s', '20 - 30s',
               '30 - 45s', '45 - 60s', '60 - 90s', '90 - 120s',
               '> 2m', '> 2m', '> 2m', '> 2m' ]
diff_age = 12
diff_age_age = None

def tty_values():
    global dev
    global pos_d
    global rtcm_thread
    global satcount_string
    global status_string
    global status_age
    global svin_string
    global tty_fd
    global log_fd

    now = datetime.datetime.now()
    if status_age == None or (now - status_age).total_seconds() > 120:
        status_string = ''

    tty_fd.write('\033[2J\033[;H')
    tty_fd.write('\n\033[32m  %.10f, %.10f\033[0m\n' % (pos_d[0][0], pos_d[0][1]))
    tty_fd.write(status_string + '\n')
    tty_fd.write(satcount_string + '\n')
    tty_fd.write(svin_string + '\n')

    log_fd.write("%s: %.10f, %.10f, %f m %s %s %s\n" % (datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S'),
        pos_d[0][0], pos_d[0][1], pos_d[0][2], status_string, satcount_string, svin_string.replace('\n', ', ')))
    log_fd.flush()

def display_values():
    global ax1
    global dev
    global pos_d
    global rtcm_thread
    global satcount_string
    global status_string
    global status_age
    global svin_string
    global log_fd

    now = datetime.datetime.now()
    if status_age == None or (now - status_age).total_seconds() > 120:
        status_string = ''

    ax1.clear()
    d_home = pos_d[0]
    d_p1 = d_home
    for d_p2 in pos_d:
        if util.gps_distance(d_home[0], d_home[1], d_p2[0], d_p2[1]) < 5:
            plot_line(d_p1, d_p2, d_home, 'ro')
            d_p1 = d_p2
    ax1.text(0.99, 0.62, "\n".join([ "%.10f, %.10f" % (pos_d[0]), status_string, satcount_string, svin_string ]),
        horizontalalignment = 'right',
        verticalalignment = 'bottom',
        transform = ax1.transAxes)

    log_fd.write("%s: %.10f, %.10f, %s %s %s\n" % (datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S'),
        pos_d[0][0], pos_d[0][1], status_string, satcount_string, svin_string.replace('\n', ', ')))
    log_fd.flush()


def read_receiver(d_func):
    global dev
    global pos_d
    global rtcm_thread
    global satcount_string
    global status_string
    global status_age
    global diff_age
    global diff_age_age
    global svin_string
    global log_fd

    ax1.clear()
    d_home = pos_d[0]
    d_p1 = d_home
    for d_p2 in pos_d:
        if util.gps_distance(d_home[0], d_home[1], d_p2[0], d_p2[1]) < 5:
            plot_line(d_p1, d_p2, d_home, 'ro')
            d_p1 = d_p2
    ax1.text(0.99, 0.62, "\n".join([ "%.10f, %.10f" % (pos_d[0]), status_string, satcount_string, svin_string ]),
        horizontalalignment = 'right',
        verticalalignment = 'bottom',
        transform = ax1.transAxes)

    log_fd.write("%s: %.10f, %.10f, %s %s %s\n" % (datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S'),
        pos_d[0][0], pos_d[0][1], status_string, satcount_string, svin_string.replace('\n', ', ')))
    log_fd.flush()

def read_receiver(d_func):
    global dev
    global pos_d
    global rtcm_thread
    global satcount_string
    global status_string
    global svin_string

    msg = dev.receive_message(ignore_eof = True)
    msg.unpack()
    # print(msg.name())
    # if msg.name() == 'NAV_POSLLH':
    #     pos = (msg.Latitude * 1.0e-7, msg.Longitude * 1.0e-7, )
    #     pos_d.appendleft(pos)
    #     d_func()
    # print(msg.name())
    if msg.name() == 'NAV_HPPOSLLH':
        lat_hp = msg.latHp
        lon_hp = msg.lonHp
        hei_hp = msg.heightHp

        if lat_hp < -99:
            print("lat_hp %d!!" % lat_hp)
            lat_hp = -99
        elif lat_hp > 99:
            print("lat_hp %d!!" % lat_hp)
            lat_hp = 99

        if lon_hp < -99:
            print("lon_hp %d!!" % lon_hp)
            lon_hp = -99
        elif lon_hp > 99:
            print("lon_hp %d!!" % lon_hp)
            lon_hp = 99

        if hei_hp < -9:
            print("hei_hp %d!!" % hei_hp)
            hei_hp = -9
        elif hei_hp > 9:
            print("hei_hp %d!!" % hei_hp)
            hei_hp = 9


        pos = (msg.lat * 1.0e-7 + lat_hp * 1.0e-9, msg.lon * 1.0e-7 + lon_hp * 1.0e-9, msg.height * 1.0e-3 + hei_hp * 1.0e-4)
        # print("NAV_HPPOSLLH hAcc= %f m" % (msg.hAcc / 10000.0))
        pos_d.appendleft(pos)
        d_func()
    # UBX-RXM-RTCM
    elif msg.name() == 'NAV_PVT':
        diff_age = (msg.flags3 >> 1) & 0x0f
        diff_age_age = datetime.datetime.now()
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
        if (msg.flags2 >> 6) & 0x03 == 0x01:
            f += '/FLOAT'
        elif (msg.flags2 >> 6) & 0x03 == 0x02:
            f += '/FIX'
        status_age = datetime.datetime.now()
        status_string = "Status: " + f + ((" Age: " + diff_age_a[diff_age]) if diff_age and (status_age - diff_age_age).total_seconds() < 300 else "")
        # print("flags= %02x %02x" % (msg.flags, msg.fixStat))

    if msg.name() != None and msg.name() != '':
        # log_fd.write("%s: %s\n" % (datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S'),
        #             msg.name()))
        # log_fd.flush()
        pass

def animate(i):
    read_receiver(display_values)

if have_display:
    ani = animation.FuncAnimation(f, animate)
    pyplot.show()
    raw_input('Press enter')
else:
    while True:
        read_receiver(tty_values)

