#!/usr/bin/env python3

import time
from random import randint
import switchyard
from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *


class Blaster:
    def __init__(
            self,
            net: switchyard.llnetbase.LLNetBase,
            blasteeIp,
            num,
            length="100",
            senderWindow="5",
            timeout="300",
            recvTimeout="100"
    ):
        # Some blaster parameters
        self.net = net
        self.mac = EthAddr('10:00:00:00:00:01')
        self.ipaddr = IPAddr('192.168.100.1')
        self.blasteeIp      = blasteeIp
        self.num            = int(num)
        self.length         = int(length)
        self.senderWindow   = int(senderWindow)
        self.extendoffset   = 1                        # index from [0, sendwindow + extendoffset]..
        self.timeout        = int(timeout)/1000
        self.recvTimeout    = int(recvTimeout)/1000

        # Timeout interrupt machanism
        self.clocker        = time.time()
        self.timetrap       = True         

        # ACK and retransmition machanism
        self.ackarray       = [False] * (self.senderWindow + self.extendoffset) # avoid being covered -- LHS is samed as RHS
        self.retranarray    = [None]  * (self.senderWindow + self.extendoffset) # the packet array for retransmition
        self.retranorient   = -1                                # point to the retranpkt.
        self.retranend      = -1                                # compose an interval with retranorient: [retranorient, retranend]
        
        # Sliding window
        self.LHS            = 0
        self.RHS            = 0                         # [LHS, RHS) RHS : next packet to be sent
        self.SW             = self.senderWindow         # [LHS,   SW) 

        # Performance measurement
        self.littleflag     = False
        self.curnum         = 0
        self.caltime        = None
        self.retranpktnum   = 0
        self.timeoutnum     = 0
        self.allbytesnum    = 0     # including retranpkt. for only payload length.     (THROUGHPUT)
        self.valbytesnum    = 0     # not including retranpkt. for only payload length. (GOODPUT)


    def handle_packet(self, recv: switchyard.llnetbase.ReceivedPacket):
        _, fromIfaceName, packet = recv
        #log_debug("I got a packet")

        # Get the sequence number
        rawheader  = packet[3].to_bytes()
        rawseqnumb = rawheader[:4]
        rawseqnumb = struct.unpack('!I', rawseqnumb)[0]
        log_debug(f"Got  a packet. the seqnumb is {rawseqnumb} ACK")

        self.ackarray[rawseqnumb]   = True      # ACK
        self.curnum += 1                        # success recv ACK, and calculate the packet num
        if self.curnum >= self.num:             # Performance measuring
            self.curnum = 0
            timestamp   = time.time() - self.caltime
            throughput  = self.allbytesnum / timestamp
            goodput     = self.valbytesnum / timestamp
            log_info(f"EVERY {self.num} PACKET!")                  # performance information
            log_info(f"Total TX time:{round(timestamp, 3)}     | Number of reTX:{self.retranpktnum} | Number of coarse TOs:{self.timeoutnum}")
            log_info(f"Throughput (Bps):{round(throughput, 3)} | Goodput (Bps):{round(goodput, 3)}")


        if rawseqnumb == self.LHS:          # LHS ACK packet, can slide the window now.
            while (self.ackarray[self.LHS] is True) and (self.LHS != self.RHS):
                self.LHS = (self.LHS + 1) % (self.senderWindow + self.extendoffset)
            self.SW = (self.LHS + self.senderWindow) % (self.senderWindow + self.extendoffset)
            self.clocker = time.time()      # update the clocker.
            log_debug(f"Now move the LHS from {rawseqnumb} to {self.LHS}.")
            log_debug(f"After moving, LHS : {self.LHS}  |  RHS : {self.RHS} | SW : {self.SW} | TRAP : {self.timetrap}")






    def handle_no_packet(self):
        log_debug("Didn't receive anything")
        sendintf = self.net.interfaces()[0]
        
        if (self.timetrap is True) and (time.time() - self.clocker >= self.timeout):     # timeout, should close the timetrap, then retransmit the packets.
            self.timetrap = False
            self.retranorient = self.LHS
            self.retranend    = self.RHS
            
            self.timeoutnum += 1
            log_debug("Timeout. prepare for retransmition.")

        if (self.timetrap == True) and ((self.RHS - self.LHS) % (self.senderWindow + self.extendoffset) < self.senderWindow):   
            # Creating the headers for the packet                                                        
            pkt = Ethernet() + IPv4() + UDP()
            pkt[1].protocol = IPProtocol.UDP

            pkt[Ethernet].src = self.mac
            pkt[Ethernet].dst = sendintf.ethaddr
            pkt[IPv4].src = self.ipaddr
            pkt[IPv4].dst = IPAddr(self.blasteeIp)

            rawseqnumb = self.RHS.to_bytes(4, byteorder='big')
            rawlength  = self.length.to_bytes(2, byteorder='big')
            rawcontent = bytes([0] * self.length)
            pkt += RawPacketContents(rawseqnumb)         # sequence number
            pkt += RawPacketContents(rawlength)          # payload  length
            pkt += RawPacketContents(rawcontent)         # payload  content

            # Do other things here and send packet
            self.retranarray[self.RHS] = pkt             # the pkt for retransmition

            #debugger()
            log_debug(f"Send a packet. the seqnumb is {self.RHS}")
            self.net.send_packet(sendintf, pkt)          # send the common packet
            self.ackarray[self.RHS] = False
            self.RHS = (self.RHS + 1) % (self.senderWindow + self.extendoffset)

            if self.littleflag is False:                # Get the time of first packet sent
                self.caltime = time.time()
                self.littleflag = True

            self.allbytesnum += self.length
            self.valbytesnum += self.length

        else:
            if self.timetrap == False:      # just retransmit 1 packet every recv-while
                log_debug(f"Retran interval is: {self.retranorient} | {self.retranend}")
                if self.retranorient == self.retranend:         # complete a traverse for the window. all retranpkt have been sent once.
                    self.clocker = time.time()    # reset the clocker
                    self.timetrap = True          # open the time trap !!!
                    self.retranorient = -1
                    self.retranend    = -1
                    log_debug("Now complete a traverse for the window. all retranpkt have been sent once.")
                    return
                
                retranpkt = self.retranarray[self.retranorient]     # Get the retranpkt

                if self.ackarray[self.retranorient] is False:
                    log_debug(f"Retransmit the pkt {self.retranorient}.")
                    self.net.send_packet(sendintf, retranpkt)
                    self.retranorient = (self.retranorient + 1) % (self.senderWindow + self.extendoffset)

                    self.retranpktnum += 1
                    self.allbytesnum  += self.length

                else:
                    while self.ackarray[self.retranorient] is True:
                        self.retranorient = (self.retranorient + 1) % (self.senderWindow + self.extendoffset)
                        if self.retranorient == self.retranend:           # complete a traverse for the window. all retranpkt have been sent once.
                            self.clocker = time.time()              # reset the clocker
                            self.timetrap = True                    # open the time trap !!!
                            self.retranorient = -1
                            self.retranend    = -1
                            log_debug("Now complete a traverse for the window. all retranpkt have been sent once.")
                            return
                    assert(self.ackarray[self.retranorient] is False)   # success get the index of retranpkt.
                    log_debug(f"Retransmit the pkt {self.retranorient}.")
                    self.net.send_packet(sendintf, retranpkt)
                    self.retranorient = (self.retranorient + 1) % (self.senderWindow + self.extendoffset)

                    self.retranpktnum += 1
                    self.allbytesnum  += self.length



    def start(self):
        '''A running daemon of the blaster.
        Receive packets until the end of time.
        '''
        while True:
            try:
                recv = self.net.recv_packet(timeout=self.recvTimeout)
            except NoPackets:
                self.handle_no_packet()
                continue
            except Shutdown:
                break

            self.handle_packet(recv)

        self.shutdown()

    def shutdown(self):
        self.net.shutdown()


def main(net, **kwargs):
    blaster = Blaster(net, **kwargs)
    blaster.start()
