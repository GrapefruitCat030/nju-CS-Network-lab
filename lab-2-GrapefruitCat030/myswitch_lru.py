'''
Ethernet learning switch in Python.

Note that this file currently has the code to implement a "hub"
in it, not a learning switch.  (I.e., it's currently a switch
that doesn't learn.)
'''
import switchyard
from switchyard.lib.userlib import *

# Use a more efficient implementation of LRU algorithm ----- hashmap + Doubly Linkedlist
# Doubly LinkedList Node
class DLLNode:
    def __init__(self, mac, intf):
        self.mac = mac
        self.intf = intf
        self.prev = None
        self.next = None

# MAC && interface
class SWITCH_CHART(object):

    def __init__(self, capacity):
        # a dict(hashMap) and a DLL for recording mac-intf couples.
		# capacity: the maximum number of items
        self.capacity = capacity
        self.SWHmap = {}
        self.head = DLLNode(0, 0)
        self.tail = DLLNode(0, 0)
        self.head.next = self.tail
        self.tail.prev = self.head
        self.count = 0

    def deleteNode(self, node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def addNode(self, node):
        node.next = self.head.next
        node.next.prev = node
        node.prev = self.head
        self.head.next = node


    def addItem(self, mac, intf):
        assert ((mac in self.SWHmap) == False)

        node = DLLNode(mac, intf)
        self.SWHmap[mac] = node
        if self.count < self.capacity:
            self.count += 1
            self.addNode(node)
        else:
            oldestnode = self.tail.prev
            del self.SWHmap[oldestnode.mac]
            self.deleteNode(oldestnode)
            self.addNode(node)
        log_info(f"****The chart add a couple: {mac} --- intf:{intf}, NOW count is {self.count}.")

    def updateLRU(self, mac):
        node = self.SWHmap[mac]
        self.deleteNode(node)
        self.addNode(node)
        log_info(f"****Update LRU now. the item:{node.mac}--{node.intf}, now is transferred to the head.")



    def changeIntf(self, mac, intf):
        oldintf = self.SWHmap[mac].intf
        self.SWHmap[mac].intf = intf
        log_info(f"****Now the src mac:{mac} intf has been changed from {oldintf} into {intf}.")


    def getIntf(self, mac):
        if not (mac in self.SWHmap):
            return False
        assert ((mac in self.SWHmap) == True)
        return self.SWHmap[mac].intf


    
    






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
                myswmem.updateLRU(eth.dst)
                myintf = myswmem.getIntf(eth.dst)
                log_info (f"Find the dst intf--{myintf}. Send packet {packet} to {myintf}.")
                net.send_packet(myintf, packet)
            else:
                for intf in my_interfaces:
                    if fromIface!= intf.name:
                        log_info (f"Flooding packet {packet} to {intf.name}")
                        net.send_packet(intf, packet)
        print("\n")

    # debugger()
    net.shutdown()
