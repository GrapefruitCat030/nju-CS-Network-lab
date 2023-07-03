#!/usr/bin/env python3

import time
import threading
from struct import pack
import switchyard
from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *


class Blastee:
    def __init__(
            self,
            net: switchyard.llnetbase.LLNetBase,
            blasterIp,
            num
    ):
        self.net = net
        self.mac = EthAddr('20:00:00:00:00:01')
        self.ipaddr = IPAddr('192.168.200.1')
        # TODO: store the parameters
        self.blasterIp = blasterIp
        self.num       = num


    def handle_packet(self, recv: switchyard.llnetbase.ReceivedPacket):
        _, fromIfaceName, packet = recv
        log_debug(f"I got a packet from {fromIfaceName}")
        log_debug(f"Pkt: {packet}")



        # Get the sequence number
        rawheader = packet[3].to_bytes()
        rawseqnumb = rawheader[0:4]
        rawlength  = rawheader[4:6]
        rawlength  = struct.unpack('>H', rawlength)[0]
        
        # Get the 8 bytes payloads.
        rawpayload = rawheader[6:6+rawlength]        # if payload length is less than 8, it will not encouter error.
        rawpayload = rawpayload[:8]
        log_info(f"Got a packet. the seqnumb is {struct.unpack('!I', rawseqnumb)[0]}")


        sendintf = self.net.interfaces()[0] 
        ackpacket = Ethernet() + IPv4(protocol=IPProtocol.UDP) + UDP()
        ackpacket[Ethernet].src = self.mac
        ackpacket[Ethernet].dst = self.net.interface_by_name(fromIfaceName).ethaddr
        ackpacket[IPv4].src = self.ipaddr
        ackpacket[IPv4].dst = IPAddr(self.blasterIp)


        ackpacket += RawPacketContents(rawseqnumb)
        ackpacket += RawPacketContents(rawpayload)

        #debugger()
        self.net.send_packet(sendintf, ackpacket)

        acknumb = struct.unpack('!I', rawseqnumb)[0]
        log_info(f"Send an ACK. the acknumb is {acknumb}")



    def start(self):
        '''A running daemon of the blastee.
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
    blastee = Blastee(net, **kwargs)
    blastee.start()
