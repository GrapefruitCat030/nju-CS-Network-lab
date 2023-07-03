'''
Ethernet learning switch in Python.

Note that this file currently has the code to implement a "hub"
in it, not a learning switch.  (I.e., it's currently a switch
that doesn't learn.)
'''
import switchyard
from switchyard.lib.userlib import *

import time

class elpsTime(object):
    def __init__(self):
        self.begin = time.time()
        self.stamp = 0
    
    def __str__(self):
        return str.format("(begin:{}, stamp:{})", self.begin, self.stamp)


class ENTRY(object):
    def __init__(self, mac, intf, elpstime):
        self.mac = mac
        self.intf = intf
        self.elpstime = elpstime

    def __str__(self):
        return str.format("ENTRY: mac:{},intf{},elpstime:{}", self.mac, self.intf, self.elpstime)


    def getstamp(self):
        self.elpstime.stamp = time.time() - self.elpstime.begin
        return self.elpstime.stamp

    def restart(self):
        self.elpstime.begin = time.time()
        self.elpstime.stamp = 0



# MAC && interface
class SWITCH_CHART(object):

    # the longest time a table item live.
    glbTimestamp = 10

    def __init__(self):
        # a dict for recording mac-intf couples.
        self.SWChart = {}

    def addItem(self, mac, intf):
        assert ((mac in self.SWChart) == False)
        # mac--[interface, elapsed_time]
        elapsed_time = elpsTime()
        entry = ENTRY(mac, intf, elapsed_time)
        self.SWChart[mac] = entry
        log_info(f"****The chart add an {entry}.")

    def get_Intf(self, mac):
        if not (mac in self.SWChart):
            return False
        assert ((mac in self.SWChart) == True)
        return self.SWChart[mac].intf

    def changeIntf(self, mac, intf):
        oldintf = self.SWChart[mac].intf
        self.SWChart[mac].intf = intf
        log_info(f"****Now the src mac:{mac} intf has been changed from {oldintf} into {intf}.")



    def get_Time(self, mac):
        assert ((mac in self.SWChart) == True)
        return self.SWChart[mac].getstamp()
    
    def setTime2zero(self, mac):
        oldtime = self.SWChart[mac].elpstime
        self.SWChart[mac].restart()
        log_info(f"****Now the src mac:{mac} time has been set from {oldtime} into {self.SWChart[mac].elpstime}.")

    def updateItems(self):
        for key in list(self.SWChart.keys()):
            temp = self.SWChart[key].getstamp()
            if temp > self.glbTimestamp:
                del self.SWChart[key]
    






def main(net: switchyard.llnetbase.LLNetBase):
    my_interfaces = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_interfaces]
    myswmem = SWITCH_CHART()

    while True:
        try:
            _, fromIface, packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            break

        log_debug (f"In {net.name} received packet {packet} on {fromIface}")
        eth = packet.get_header(Ethernet)
        
        # check the Table Item timestamp
        myswmem.updateItems()        
        
        if eth is None:
            log_info("Received a non-Ethernet packet?!")
            return
        
        # self-learning in switch, add a src_mac---intf couple
        if not myswmem.get_Intf(eth.src) :
            myswmem.addItem(eth.src, fromIface) 

        if eth.dst in mymacs:
            log_info("Received a packet intended for me")

        else:
            # check if the incoming port for packet same as the port info in table.
            if (fromIface != (myswmem.get_Intf(eth.src))):
                myswmem.changeIntf(eth.src, fromIface)
                myswmem.setTime2zero(eth.src)
            else:
                myswmem.setTime2zero(eth.src)


            # before forwarding, check if the dst mac is exist in chart
            # if so, forward it through the intf that is recorded relatively
            if myswmem.get_Intf(eth.dst):
                myintf = myswmem.get_Intf(eth.dst)
                log_info (f"Find the dst intf--{myintf}. Send packet {packet}.")
                net.send_packet(myintf, packet)
            else:
                for intf in my_interfaces:
                    if fromIface!= intf.name:
                        log_info (f"Flooding packet {packet} to {intf.name}")
                        net.send_packet(intf, packet)
        print("\n")

    # debugger()
    net.shutdown()
