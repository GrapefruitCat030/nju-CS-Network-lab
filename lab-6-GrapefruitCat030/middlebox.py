#!/usr/bin/env python3

import time
import threading
from random import randint

import switchyard
from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *


class Middlebox:
    def __init__(
            self,
            net: switchyard.llnetbase.LLNetBase,
            dropRate="0.19"
    ):
        self.net = net
        self.dropRate = float(dropRate)

    def handle_packet(self, recv: switchyard.llnetbase.ReceivedPacket):
        _, fromIfaceName, packet = recv
        if fromIfaceName == "middlebox-eth0":                         # blaster->blastee
            log_debug("Received from blaster")
            '''
            Received data packet
            Should I drop it?
            If not, modify headers & send to blastee
            '''      
            # use a random lib to drop the packet
            randomint = randint(1,100)
            if randomint <= self.dropRate * 100:
                return;

            otherintf = self.net.interface_by_name("middlebox-eth1")
            assert(otherintf is not None)
            packet[Ethernet].src = otherintf.ethaddr
            packet[Ethernet].dst = EthAddr('20:00:00:00:00:01')        # blastee

            self.net.send_packet("middlebox-eth1", packet)

        elif fromIfaceName == "middlebox-eth1":                        # blastee->blaster
            log_debug("Received from blastee")
            '''
            Received ACK
            Modify headers & send to blaster. Not dropping ACK packets!
            net.send_packet("middlebox-eth0", pkt)
            '''
            otherintf = self.net.interface_by_name("middlebox-eth0")
            assert(otherintf is not None)
            packet[Ethernet].src = otherintf.ethaddr
            packet[Ethernet].dst = EthAddr('10:00:00:00:00:01')        # blaster

            self.net.send_packet("middlebox-eth0", packet)
        else:
            log_debug("Oops :))")

    def start(self):
        '''A running daemon of the router.
        Receive packets until the end of time.
        '''
        while True:
            try:
                recv = self.net.recv_packet(timeout=1.0)
            except NoPackets:
                continue
            except Shutdown:
                break

            self.handle_packet(recv)

        self.shutdown()

    def shutdown(self):
        self.net.shutdown()


def main(net, **kwargs):
    middlebox = Middlebox(net, **kwargs)
    middlebox.start()
