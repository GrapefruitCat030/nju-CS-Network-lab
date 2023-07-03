'''
Ethernet learning switch in Python.

Note that this file currently has the code to implement a "hub"
in it, not a learning switch.  (I.e., it's currently a switch
that doesn't learn.)
'''
import switchyard
from switchyard.lib.userlib import *



# MAC && interface
class SWITCH_CHART(object):
    def __init__(self):
        # a dict for recording mac-intf couples.
        self.SWChart = {}

    def addItem(self, mac, intf):
        assert ((mac in self.SWChart) == False)
        self.SWChart[mac] = intf
        log_info(f"the chart add a couple: {mac} --- {intf}")

    def getIntf(self, mac):
        assert ((mac in self.SWChart)== True)
        return self.SWChart[mac]

    def changeIntf(self, mac, intf):
        oldintf = self.SWChart[mac]
        self.SWChart[mac].intf = intf
        log_info(f"****Now the src mac:{mac} intf has been changed from {oldintf} into {self.SWChart[mac]}.")

    






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
        if eth is None:
            log_info("Received a non-Ethernet packet?!")
            return
        
        # self-learning in switch, add a mac-intf couple
        if eth.src not in myswmem.SWChart :
            myswmem.addItem(eth.src, fromIface)

        if eth.dst in mymacs:
            log_info("Received a packet intended for me")
        else:
            # check if the incoming port for packet same as the port info in table.
            if (fromIface != (myswmem.getIntf(eth.src))):
                myswmem.changeIntf(eth.src, fromIface)

            # before forwarding, check if the dst mac is exist in chart
            # if so, forward it through the intf that is recorded relatively
            if eth.dst in myswmem.SWChart:
                myintf = myswmem.SWChart[eth.dst]
                log_info (f"Find the intf--{myintf}. Send packet {packet} to {myintf}.")
                net.send_packet(myintf, packet)
            else:
                for intf in my_interfaces:
                    if fromIface!= intf.name:
                        log_info (f"Flooding packet {packet} to {intf.name}")
                        net.send_packet(intf, packet)

    net.shutdown()
