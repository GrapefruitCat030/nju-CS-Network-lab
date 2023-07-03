#!/usr/bin/env python3

'''
Basic IPv4 router (static routing) in Python.
'''

import time
import switchyard
from switchyard.lib.userlib import *

class elpsTime(object):
    def __init__(self):
        self.begin = time.time()
        self.stamp = 0
    
    def __str__(self):
        return str.format("(begin:{}, stamp:{})", self.begin, self.stamp)


class ENTRY(object):
    def __init__(self, ip, mac, elpstime):
        self.ip = ip
        self.mac = mac
        self.elpstime = elpstime

    def __str__(self):
        return "ENTRY: ip:{} | mac:{} | elpstime:{}".format(self.ip, self.mac, self.elpstime)

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
        assert ((mac in self.table) == False)
        elapsed_time = elpsTime()
        entry = ENTRY(ip, mac, elapsed_time)
        self.table[ip] = entry
        log_info(f"****The chart add an {entry}.")
        self.print_table()


    def get_mac(self, ip):
        if not (ip in self.table):
            return False
        assert ((ip in self.table) == True)
        return self.table[ip].mac

    def change_mac(self, ip, mac):
        oldmac = self.table[ip].mac
        self.table[ip].mac = mac
        log_info(f"****Now the src: {ip} has been changed from {oldmac} into {mac}.")

    def get_Time(self, ip):
        assert ((ip in self.table) == True)
        return self.table[ip].getstamp()
    
    def setTime2zero(self, ip):
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
 

class Router(object):
    def __init__(self, net: switchyard.llnetbase.LLNetBase):
        self.net = net
        # other initialization stuff here
        self.my_interfaces = net.interfaces()
        self.APR_CACHE = ARP_CACHE()

    def handle_packet(self, recv: switchyard.llnetbase.ReceivedPacket):
        timestamp, ifaceName, packet = recv
        captureIntf = self.net.interface_by_name(ifaceName)
        # TODO: your logic here

        arp = packet.get_header(Arp)
        eth = packet.get_header(Ethernet)

        # lab 3 requirement: omit packets exclude ARP.
        if not arp:
            log_info("____The packet is not an ARP.____")
            return None
        assert (arp)

        # faq: check Ethernet header first.
        if (eth.dst != EthAddr('ff:ff:ff:ff:ff:ff')) and (eth.dst != captureIntf.ethaddr):
            return None

        for intf in self.my_interfaces:
            # determine whether the arp's dst IP is held by a port of the router.
            # if so, do the processing. 
            if arp.targetprotoaddr == intf.ipaddr:

                # in any case, update the arp cache after ARP identified that is dested to router.
                # Attention: a router MUST not believe any ARP reply that 
                #            claims that the Ethernet address of another host or router is a broadcast address.
                if arp.senderhwaddr != EthAddr('ff:ff:ff:ff:ff:ff'):
                    if (not self.APR_CACHE.get_mac(arp.senderprotoaddr)):
                        self.APR_CACHE.addItem(arp.senderprotoaddr, arp.senderhwaddr)
                    else:
                        # firstly update the elapsed time.
                        self.APR_CACHE.setTime2zero(arp.senderprotoaddr)
                        # check whether the src MAC is same as the MAC i n existed entry.
                        if not (arp.senderhwaddr == self.APR_CACHE.get_mac(arp.senderprotoaddr)):
                            self.APR_CACHE.change_mac(arp.senderprotoaddr, arp.senderhwaddr)


                # Hoding a ARP request, prepare to forward the ARP reply.
                if arp.operation == ArpOperation.Request: 
                    # make a ARP respond through proper interface.
                    rpacket = create_ip_arp_reply(intf.ethaddr, arp.senderhwaddr, arp.targetprotoaddr, arp.senderprotoaddr)

                    # there is a possible case that ARP requested interface B but captured by interface A. 
                    self.net.send_packet(captureIntf, rpacket)
                    log_info(f"****The packet __{rpacket}__ is sent by {ifaceName}.")
                    return 0
        log_info("____Haha, there is no relative intf.____")


    def start(self):
        '''A running daemon of the router.
        Receive packets until the end of time.
        '''
        log_info(f"****That is my interface!{self.net.interfaces()}")
        while True:
            try:
                recv = self.net.recv_packet(timeout=1.0)
            except NoPackets:
                continue
            except Shutdown:
                break
            
            self.APR_CACHE.updateItems()
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
