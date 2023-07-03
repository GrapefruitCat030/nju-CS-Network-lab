'''
Ethernet learning switch in Python.

Note that this file currently has the code to implement a "hub"
in it, not a learning switch.  (I.e., it's currently a switch
that doesn't learn.)
'''
import switchyard
from switchyard.lib.userlib import *
import heapq

class ENTRY(object):
    def __init__(self, mac, intf, volume):
        self.mac = mac
        self.intf = intf
        self.volume = volume
    
    def __str__(self):
        return str.format("Entry: mac:{}, intf:{}, volume:{}", self.mac, self.intf, self.volume)

    def __lt__(self, other):
        return self.volume < other.volume
    
    def __gt__(self, other):
        return other.__lt__(self)
    
    def __eq__(self, other):
        return self.volume == other.volume
    
    def __ne__(self, other):
        return not self.__eq__(other)


# Use a more efficient implementation of Traffic Control (LTV) algorithm ----- Min Heap
# the structure of Hashmap is: (mac, ENTRY), among it the ENTRY'structure is [mac, intf, volume]
# MAC && interface
class SWITCH_CHART(object):

    def __init__(self, capacity):
        # a dict(hashMap) and a DLL for recording mac-intf couples.
		# capacity: the maximum number of items
        self.capacity = capacity
        self.SWmap = {}
        self.SWheap = []
        self.count = 0

    def addItem(self, mac, intf):
        assert ((mac in self.SWmap) == False)

        node = ENTRY(mac, intf, 0)
        self.SWmap[mac] = node
        if self.count < self.capacity:
            self.count += 1
            heapq.heappush(self.SWheap, node) 
            log_info(f"****The chart is not full.Add an {node}, NOW count is {self.count}.")
        else:
            oldestnode = self.SWheap[0]     # get the lowest volume entry
            heapq.heappop(self.SWheap)      # and then delete it from Hashmap and heap.
            del self.SWmap[oldestnode.mac]

            heapq.heappush(self.SWheap, node) 
            log_info(f"****Full chart!! delete old {oldestnode}, add an new {node}. NOW count is {self.count}")
            for n in self.SWheap:
                print("    the table item: {}", n)
            print("\n")


    def changeIntf(self, mac, intf):
        oldnode = self.SWmap[mac]
        self.SWmap[mac].intf = intf
        log_info(f"****Now the src mac:{mac} intf has been changed from {oldnode} into {self.SWmap[mac]}.")


    def getIntf(self, mac):
        if not (mac in self.SWmap):
            return False
        assert ((mac in self.SWmap) == True)
        return self.SWmap[mac].intf

    def updateLTV(self, mac):
        assert ((mac in self.SWmap) == True)
        node = self.SWmap[mac]
        node.volume += 1
        heapq.heapify(self.SWheap) 

    
    






def main(net: switchyard.llnetbase.LLNetBase):
    my_interfaces = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_interfaces]
    # give switch memory a max items numb
    myswmem = SWITCH_CHART(5)

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
        
        # Self-learning in switch
        # firstly judged whether the table is full or not, then add an item.
        if not myswmem.getIntf(eth.src) :
            myswmem.addItem(eth.src, fromIface) 
        # judge if the intf be same as the old.
        else:
            if (fromIface != myswmem.getIntf(eth.src)): 
                myswmem.changeIntf(eth.src, fromIface)



        if eth.dst in mymacs:
            log_info("Received a packet intended for me.")
            

        else:

            # before forwarding, check if the dst mac is exist in chart
            # if so, forward it through the intf that is recorded relatively
            # Specially, LRU's USE is refered to the Dst using rather than Src.
            if myswmem.getIntf(eth.dst):
                myswmem.updateLTV(eth.dst)
                myintf = myswmem.getIntf(eth.dst)
                log_info (f"Find the dst intf--{myintf} and send it out.Now the volume change:{myswmem.SWmap[eth.dst]}.")
                net.send_packet(myintf, packet)
            else:
                for intf in my_interfaces:
                    if fromIface!= intf.name:
                        log_info (f"Flooding packet {packet} to {intf.name}")
                        net.send_packet(intf, packet)
        print("\n")

    # debugger()
    net.shutdown()
