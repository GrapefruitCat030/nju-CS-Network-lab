#!/usr/bin/env python3

'''
Basic IPv4 router (static routing) in Python.
'''

import time
import switchyard
from switchyard.lib.userlib import *
from enum import Enum
import inspect
from copy import deepcopy

DEBUG = False



class State(Enum):
    iscommon = 1
    isarp = 2
    isicmp = 3

class retranState(Enum):
    NO_TIMEOUT = 0
    UNIT_TIMEOUT = 1
    THOUROUGH_TIMEOUT = 2
    SEND_ARPOK = 3

def custom_assert(condition, message="Assertion failed"):
    if not condition:
        frame = inspect.currentframe().f_back
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        raise AssertionError(f"{message} [File: {filename}, Line: {lineno}]")

class elpsTime(object):
    def __init__(self):
        self.begin = time.time()
        self.stamp = 0
    
    def __str__(self):
        return str.format("(begin:{}, stamp:{})", self.begin, self.stamp)

class ARP_ENTRY(object):
    def __init__(self, ip, mac, elpstime):
        self.ip = ip
        self.mac = mac
        self.elpstime = elpstime

    def __str__(self):
        return "ARP_ENTRY: ip:{} | mac:{} | elpstime:{}".format(self.ip, self.mac, self.elpstime)

    def getstamp(self):
        self.elpstime.stamp = time.time() - self.elpstime.begin
        return self.elpstime.stamp

    def restart(self):
        self.elpstime.begin = time.time()
        self.elpstime.stamp = 0

class ARP_CACHE(object):

    # the longest time a table item live.
    glbTimestamp = 100

    def __init__(self):
        # a dict for recording mac-intf couples.
        self.table = {}

    def addItem(self, ip, mac):
        custom_assert ((mac in self.table) == False)
        elapsed_time = elpsTime()
        entry = ARP_ENTRY(ip, mac, elapsed_time)
        self.table[ip] = entry
        log_info(f"****The chart add an {entry}.")
        self.print_table()


    def get_mac(self, ip):
        if not (ip in self.table):
            return None
        custom_assert ((ip in self.table) == True)
        return self.table[ip].mac

    def change_mac(self, ip, mac):
        if ip not in self.table:
            return None
        oldmac = self.table[ip].mac
        self.table[ip].mac = mac
        log_info(f"****Now the src: {ip} has been changed from {oldmac} into {mac}.")

    def get_Time(self, ip):
        custom_assert ((ip in self.table) == True)
        return self.table[ip].getstamp()
    
    def setTime2zero(self, ip):
        if ip not in self.table:
            return None
        oldtime = self.table[ip].elpstime
        self.table[ip].restart()
        log_info(f"****Now the src: {ip} time has been set from {oldtime} into {self.table[ip].elpstime}.")

    def updateItems(self):
        for key in list(self.table.keys()):
            temp = self.table[key].getstamp()
            if temp > self.glbTimestamp:
                log_info("____An entry removed. entry: {self.table[key]}____")
                del self.table[key]

    def print_table(self):
        print("\nNow the table is update.")
        for key in self.table:
            print(f"{self.table[key]}")
        print("\n")
 

class ROUTE_ENTRY:
    def __init__(self, netprefix, mask, next_hop, interface):
        self.netprefix = netprefix
        self.mask = mask
        self.next_hop = next_hop
        self.interface = interface

        custom_assert(isinstance(netprefix, IPv4Address))
        custom_assert(isinstance(mask, IPv4Address))
        custom_assert(isinstance(next_hop, IPv4Address))
        custom_assert(isinstance(interface, Interface))

    def __str__(self) -> str:
        return f'netprefix:{self.netprefix}, netmask:{self.mask}, next_hop:{self.next_hop}, intf:{self.interface.name}'

class ROUTER_TABLE(object):
    def __init__(self, net):
        self.net = net
        self.interface_list = net.interfaces()
        self.entry_list = self.createtable()
        
        custom_assert(isinstance(self.entry_list, list))
    
    def createtable(self):
        rc = []

        # first, use the interface_list to create a initial table.
        for interface in self.interface_list:
            tempip = interface.ipaddr
            tempmask = interface.netmask
            
            custom_assert(isinstance(tempip, IPv4Address))
            custom_assert (isinstance(tempmask, IPv4Address))

            netprefix = IPv4Address(int(tempip) & int(tempmask))
            netmask = tempmask
            temphop = IPv4Address('0.0.0.0')
            
            tempentry = ROUTE_ENTRY(netprefix, netmask, temphop, interface)
            rc.append(tempentry)


        # second, read the context saved in the txt to append the table. each line in txt is a table entry.
        with open('forwarding_table.txt', 'r') as file:
            for line in file:
                values = line.split()
                prefix = IPv4Address(values[0])
                mask =  IPv4Address(values[1])
                hop =  IPv4Address(values[2])
                intf = self.net.interface_by_name(values[3]) 
                entryfromfile = ROUTE_ENTRY(prefix, mask, hop, intf)
                rc.append(entryfromfile)

        return rc

    # ATTENTION: the instance LPM returning is ROUTE_ENTRY. 
    def LPM(self, dstipaddr):
        custom_assert(isinstance(dstipaddr, IPv4Address))
        maxmasklen = -1
        rcentry = None
        
        for entry in self.entry_list:
            tempprefix = entry.netprefix
            tempmask = entry.mask

            matches = ((int(tempmask) & int(dstipaddr)) == int(tempprefix))
            if matches:
                if maxmasklen <= int(tempmask):
                    rcentry = entry
                    maxmasklen = int(tempmask)
                else:
                    continue

        debugger() if DEBUG else None
        if rcentry == None:
            print(f"Fail. there is no entry suitable for {dstipaddr}")
        return rcentry

class ARP_2b_REPLY(object):
    def __init__(self, next_ip, next_mac, next_intf, elpstime, arprequestpkt):
        self.next_ip = next_ip
        self.next_mac = next_mac
        self.next_intf = next_intf
        self.elpstime = elpstime
        self.arprequestpkt = arprequestpkt
        self.pkt_list = []
        self.number = 1

    def __str__(self):
        return "ARP_2b_REPLY: next_ip:{} | next_mac:{} | elpstime:{} | arppkt:{} \n pktlist:{}"\
            .format(self.next_ip, self.next_mac, self.elpstime, self.arprequestpkt, self.pkt_list)
        
    def getstamp(self):
        self.elpstime.stamp = time.time() - self.elpstime.begin
        return self.elpstime.stamp

    def retransmitjudge(self, timeout = 1.0)->retranState:
        jdgtime = self.getstamp()
        assert(self.arprequestpkt is not None)
        assert(self.arprequestpkt[Arp] is not None)
        # has got the dst mac, hence sending it.
        if self.next_mac is not None:
            return retranState.SEND_ARPOK
        else:
            if (jdgtime > timeout) and (self.number < 5):
                self.elpstime.begin = time.time()
                self.elpstime.stamp = 0
                print(f"\nadd 1 . add 1. now {self.number}")
                return retranState.UNIT_TIMEOUT
            # wait for the fifth arp reply.
            elif (jdgtime <= timeout) and (self.number == 5):
                return retranState.NO_TIMEOUT
            elif self.number >= 5:
                return retranState.THOUROUGH_TIMEOUT
            else:
                return retranState.NO_TIMEOUT


class Router(object):
    def __init__(self, net: switchyard.llnetbase.LLNetBase):
        self.net = net
        # other initialization stuff here
        self.my_interfaces = net.interfaces()
        self.arp_cache = ARP_CACHE()
        self.router_table = ROUTER_TABLE(net)
        self.arp_resolved_queue = {}

    def printtable(self):
        for entry in self.router_table.entry_list:
            print(entry)

    def arp_operation(self, arp, captureIntf):

        # in any case, update the arp cache after ARP identified that is dested to router.
        # Attention: a router MUST not believe any ARP reply that 
        #            claims that the Ethernet address of another host or router is a broadcast address.
        if arp.operation == ArpOperation.Reply:
            if (arp.senderhwaddr == EthAddr('ff:ff:ff:ff:ff:ff')):
                return None
            else:
                for intf in self.my_interfaces:
                    # determine whether the arp's dst IP is held by a port of the router.
                    # if so, do the processing. 
                    if arp.targetprotoaddr == intf.ipaddr:
                        if (not self.arp_cache.get_mac(arp.senderprotoaddr)):
                            self.arp_cache.addItem(arp.senderprotoaddr, arp.senderhwaddr)
                        else:
                            # firstly update the elapsed time.
                            self.arp_cache.setTime2zero(arp.senderprotoaddr)
                            # check whether the src MAC is same as the MAC i n existed entry.
                            if not (arp.senderhwaddr == self.arp_cache.get_mac(arp.senderprotoaddr)):
                                self.arp_cache.change_mac(arp.senderprotoaddr, arp.senderhwaddr)

        if arp.operation == ArpOperation.Request:
            for intf in self.my_interfaces:
                # determine whether the arp's dst IP is held by a port of the router.
                # if so, do the processing. 
                if arp.targetprotoaddr == intf.ipaddr:

                    if (not self.arp_cache.get_mac(arp.senderprotoaddr)):
                        self.arp_cache.addItem(arp.senderprotoaddr, arp.senderhwaddr)
                    else:
                        # firstly update the elapsed time.
                        self.arp_cache.setTime2zero(arp.senderprotoaddr)
                        # check whether the src MAC is same as the MAC i n existed entry.
                        if not (arp.senderhwaddr == self.arp_cache.get_mac(arp.senderprotoaddr)):
                            self.arp_cache.change_mac(arp.senderprotoaddr, arp.senderhwaddr)

                    # Hoding a ARP request, prepare to forward the ARP reply.
                    # make a ARP respond through proper interface.
                    rpacket = create_ip_arp_reply(intf.ethaddr, arp.senderhwaddr, arp.targetprotoaddr, arp.senderprotoaddr)

                    # there is a possible case that ARP requested interface B but captured by interface A. 
                    self.net.send_packet(captureIntf, rpacket)
                    log_info(f"****The packet __{rpacket}__ is sent by {captureIntf.name}.")





        log_info("____Haha, there is no relative intf.____")

    def handle_packet(self, recv: switchyard.llnetbase.ReceivedPacket):
        timestamp, ifaceName, packet = recv
        captureIntf = self.net.interface_by_name(ifaceName)


        # use a variable "flag" to distinguish the states of a received packet.
        flag = None

        eth = packet.get_header(Ethernet)
        
        if eth.ethertype == 0x8100:
            return None


        arp = packet.get_header(Arp)
        ip4 = packet.get_header(IPv4)
        dstipaddr = None

        custom_assert(eth is not None)

        # lab 3 requirement: omit packets exclude ARP.
        # lab 4 omit this rules.
        if arp is None:
            log_info("____The packet is not an ARP.____")
            custom_assert(ip4 is not None)
            flag = State.iscommon
            dstipaddr = ip4.dst
        else:
            custom_assert(ip4 is None)
            dstipaddr = arp.targetprotoaddr
            flag = State.isarp


        # If the Ethernet destination is neither a broadcast address nor the MAC of the incoming port, 
        # the router should always drop it instead of going through the looking up process.
        if (eth.dst != EthAddr('ff:ff:ff:ff:ff:ff')) and (eth.dst != captureIntf.ethaddr):
            return None
        
        # If there is no match in the table, drop the packet for now.
        destentry = self.router_table.LPM(dstipaddr)
        if destentry == None:
            return None
        
        print(f"\n{packet} destentry is {destentry}\n")
        # If a packet is for the router itself (i.e., destination address is among the router's interfaces), just drop/ignore the packet.
        if flag is not State.isarp:
            for intf in self.my_interfaces:
                if intf.ipaddr == dstipaddr:
                    print("drop it! drop it!")
                    return None


        if flag == State.isarp:
            custom_assert(isinstance(arp, Arp), f"isinstance({arp}, Arp)")
            self.arp_operation(arp, captureIntf)

        elif flag == State.iscommon:

            if destentry.next_hop == IPv4Address('0.0.0.0'):
                next_ip = dstipaddr
            else:
                next_ip = destentry.next_hop 

            next_mac = self.arp_cache.get_mac(next_ip) 

            next_intf = destentry.interface
            arppacket = None

            # Need to send an ARP query in order to obtain the Ethernet address
            if next_mac is None:
                arppacket = create_ip_arp_request(next_intf.ethaddr, next_intf.ipaddr, next_ip)

                # if next_ip saved the arp request before, dont send it again.
                if str(next_ip) not in self.arp_resolved_queue:
                    self.net.send_packet(next_intf, arppacket)                   


            # Create a new Ethernet header for the IP packet to be forwarded.
            newpacket = deepcopy(packet)

            print(f"{next_ip} DETECT. {newpacket}")
            newpacket[Ethernet].src = next_intf.ethaddr
            newpacket[Ethernet].dst = next_mac
            newpacket[IPv4].ttl -= 1

            if next_mac is not None:
                
                self.net.send_packet(next_intf, newpacket)
                return None

            custom_assert(next_mac == None)

            # add it to the resolved queue. 
            if str(next_ip) not in self.arp_resolved_queue:
                newitem = ARP_2b_REPLY(next_ip, next_mac, next_intf, elpsTime(), arppacket)
                newitem.pkt_list.append(newpacket)
                self.arp_resolved_queue[str(next_ip)] = newitem
            else:
                self.arp_resolved_queue[str(next_ip)].pkt_list.append(newpacket)






    def queueoperate(self):
        if len(self.arp_resolved_queue) == 0:
            return None
        
        # resolve the arp in queue
        for dealip, item in list(self.arp_resolved_queue.items()):
            assert(isinstance(item, ARP_2b_REPLY))
            assert(dealip == str(item.next_ip))

            # update the dst mac from the arp cache.
            item.next_mac = self.arp_cache.get_mac(item.next_ip)
            for pkt in item.pkt_list:
                pkt[Ethernet].dst = item.next_mac

            temprc = item.retransmitjudge()

            if temprc is retranState.SEND_ARPOK:
                for pkt in item.pkt_list:
                    print(f"LOGGGGGG : {pkt}")
                for pkt in item.pkt_list:
                    # if (EthAddr('20:00:00:00:00:01') == pkt[Ethernet].src) and (EthAddr('30:00:00:00:01:04') == pkt[Ethernet].dst):
                    #     debugger()
                    #     pkt[IPv4].ttl = 34
                    self.net.send_packet(item.next_intf, pkt)
                print(f"DELETE : delete the item for retransmit.{item}\n")
                del self.arp_resolved_queue[dealip]

            elif temprc is retranState.NO_TIMEOUT:
                assert( (item.next_mac == None))
                continue
            elif temprc is retranState.UNIT_TIMEOUT:
                assert((item.next_mac == None))
                item.number += 1
                self.net.send_packet(item.next_intf, item.arprequestpkt)
            elif (temprc is retranState.THOUROUGH_TIMEOUT):
                assert( (item.next_mac == None))
                assert(item.number >= 5)
                print(f"DELETE : delete the item for retransmit.{item}\n")
                del self.arp_resolved_queue[dealip]
            else:
                custom_assert(0)


    def start(self):

       #custom_assert(0, "it should be 1")

        '''A running daemon of the router.
        Receive packets until the end of time.
        '''
        log_info(f"****That is my interface!{self.net.interfaces()}")
        self.printtable()


        while True:
            self.queueoperate()

            try:
                recv = self.net.recv_packet(timeout=1.0)
            except NoPackets:
                continue
            except Shutdown:
                break
            
            self.arp_cache.updateItems()
            self.handle_packet(recv)

        self.stop()

    def stop(self):
        self.net.shutdown()


def main(net):
    '''
    Main entry point for router.  Just create Router
    object and get it going.
    '''
    router = Router(net)
    router.start()
