from switchyard.lib.userlib import *
import time

def new_packet(hwsrc, hwdst, ipsrc, ipdst, reply=False):
    ether = Ethernet(src=hwsrc, dst=hwdst, ethertype=EtherType.IP)
    ippkt = IPv4(src=ipsrc, dst=ipdst, protocol=IPProtocol.ICMP, ttl=32)
    icmppkt = ICMP()
    if reply:
        icmppkt.icmptype = ICMPType.EchoReply
    else:
        icmppkt.icmptype = ICMPType.EchoRequest
    return ether + ippkt + icmppkt


def test_hub():
    s = TestScenario("switch tests")
    s.add_interface('eth0', '10:00:00:00:00:01')
    s.add_interface('eth1', '10:00:00:00:00:02')
    s.add_interface('eth2', '10:00:00:00:00:03')
    s.add_interface('eth3', '10:00:00:00:00:04')
    s.add_interface('eth4', '10:00:00:00:00:05')

    # test case 1: a frame with broadcast destination should get sent out
    # all ports except ingress
    testpkt = new_packet(
        "30:00:00:00:00:02",
        "ff:ff:ff:ff:ff:ff",
        "172.16.42.2",
        "255.255.255.255"
    )
    s.expect(
        PacketInputEvent("eth1", testpkt, display=Ethernet),
        ("An Ethernet frame with a broadcast destination address "
         "should arrive on eth1")
    )
    s.expect(
        PacketOutputEvent("eth0", testpkt, "eth2", testpkt, "eth3", testpkt, "eth4", testpkt, display=Ethernet),
        ("The Ethernet frame with a broadcast destination address should be "
         "forwarded out ports eth0, eth2, eth3, and eth4.")
    )

    # test case 2: a frame with any unicast address except one assigned to switch
    # interface should be sent out all ports except ingress, since the mac not found in swChart.
    # But the respond packet should be sent out the reqpkt's ingress.
    reqpkt = new_packet(
        "20:00:00:00:00:01",
        "30:00:00:00:00:33",
        '192.168.1.100',
        '172.16.42.33'
    )
    s.expect(
        PacketInputEvent("eth0", reqpkt, display=Ethernet),
        ("An Ethernet frame from 20:00:00:00:00:01 to 30:00:00:00:00:33 "
         "should arrive on eth0")
    )
    s.expect(
        PacketOutputEvent("eth1", reqpkt, "eth2", reqpkt, "eth3", reqpkt, "eth4", reqpkt, display=Ethernet),
        ("Ethernet frame destined for 30:00:00:00:00:33 should be flooded out"
         " eth1,2,3 and 4")
    )

    resppkt = new_packet(
        "30:00:00:00:00:33",
        "20:00:00:00:00:01",
        '172.16.42.33',
        '192.168.1.100',
        reply=True
    )
    s.expect(
        PacketInputEvent("eth1", resppkt, display=Ethernet),
        ("An Ethernet frame from 30:00:00:00:00:02 to 20:00:00:00:00:01 "
         "should arrive on eth1")
    )
    s.expect(
        PacketOutputEvent("eth0", resppkt, display=Ethernet),
        ("Ethernet frame destined to 20:00:00:00:00:01 should be sent out only"
         "eth0 ")
    )

    # test case 3: a frame with dest address of one of the interfaces should
    # result in nothing happening
    reqpkt = new_packet(
        "20:00:00:00:00:01",
        "10:00:00:00:00:03",
        '192.168.1.100',
        '172.16.42.2'
    )
    s.expect(
        PacketInputEvent("eth2", reqpkt, display=Ethernet),
        ("An Ethernet frame should arrive on eth2 with destination address "
         "the same as eth2's MAC address"
         "the ingress should be changed from eth0 to eth 2")
    )
    s.expect(
        PacketInputTimeoutEvent(1.0),
        ("The switch should not do anything in response to a frame arriving with"
         " a destination address referring to the switch itself.")
    )

    # test case 4: LRU test
    
    # time.sleep(10)

    pktA = new_packet(
        "60:00:00:00:00:01",
        "90:00:00:00:00:00",
        '6.5.4.1',
        '9.8.7.6'
    )
    s.expect(
        PacketInputEvent("eth0", pktA, display=Ethernet),
        ("pktA should arrive on eth0")
    )
    s.expect(
        PacketOutputEvent("eth1", pktA, "eth2", pktA, "eth3", pktA, "eth4", pktA, display=Ethernet),
        ("Ethernet frame destined for 90:00:00:00:00:00 should be flooded out"
         " eth1,2,3 and 4")
    )

    pktB = new_packet(
        "60:00:00:00:00:02",
        "90:00:00:00:00:00",
        '6.5.4.2',
        '9.8.7.6'
    )
    s.expect(
        PacketInputEvent("eth1", pktB, display=Ethernet),
        ("pktB should arrive on eth1")
    )
    s.expect(
        PacketOutputEvent("eth0", pktB, "eth2", pktB, "eth3", pktB, "eth4", pktB, display=Ethernet),
        ("Ethernet frame destined for 90:00:00:00:00:00 should be flooded out"
         " eth0,2,3 and 4")
    )

    pktC = new_packet(
        "60:00:00:00:00:03",
        "90:00:00:00:00:00",
        '6.5.4.3',
        '9.8.7.6'
    )
    s.expect(
        PacketInputEvent("eth2", pktC, display=Ethernet),
        ("pktC should arrive on eth2")
    )
    s.expect(
        PacketOutputEvent("eth0", pktC, "eth1", pktC, "eth3", pktC, "eth4", pktC, display=Ethernet),
        ("Ethernet frame destined for 90:00:00:00:00:00 should be flooded out"
         " eth0,1,3 and 4")
    )

    pktD = new_packet(
        "60:00:00:00:00:04",
        "90:00:00:00:00:00",
        '6.5.4.4',
        '9.8.7.6'
    )
    s.expect(
        PacketInputEvent("eth3", pktD, display=Ethernet),
        ("pktD should arrive on eth3")
    )
    s.expect(
        PacketOutputEvent("eth0", pktD, "eth1", pktD, "eth2", pktD, "eth4", pktD, display=Ethernet),
        ("Ethernet frame destined for 90:00:00:00:00:00 should be flooded out"
         " eth0,1,2 and 4")
    )

    pktE = new_packet(
        "60:00:00:00:00:05",
        "90:00:00:00:00:00",
        '6.5.4.5',
        '9.8.7.6'
    )
    s.expect(
        PacketInputEvent("eth4", pktE, display=Ethernet),
        ("pktE should arrive on eth4")
    )
    s.expect(
        PacketOutputEvent("eth0", pktE, "eth1", pktE, "eth2", pktE, "eth3", pktE, display=Ethernet),
        ("Ethernet frame destined for 90:00:00:00:00:00 should be flooded out"
         " eth0,1,2 and 3")
    )

    pktF = new_packet(
        "60:00:00:00:00:06",
        "90:00:00:00:00:00",
        '6.5.4.6',
        '9.8.7.6'
    )
    s.expect(
        PacketInputEvent("eth0", pktF, display=Ethernet),
        ("pktF should arrive on eth0, hence squeezing the pktA's item.")
    )
    s.expect(
        PacketOutputEvent("eth4", pktF, "eth1", pktF, "eth2", pktF, "eth3", pktF, display=Ethernet),
        ("Ethernet frame destined for 90:00:00:00:00:00 should be flooded out"
         " eth4,1,2 and 3")
    )

    srcApkt = new_packet(
        "90:00:00:00:00:00",
        "60:00:00:00:00:01",
        '9.8.7.6',
        '6.5.4.1'
    )
    s.expect(
        PacketInputEvent("eth4", srcApkt, display=Ethernet),
        ("the srcApkt arrive on eth4.")
    )
    s.expect(
        PacketOutputEvent("eth0", srcApkt,"eth1", srcApkt,"eth2", srcApkt,"eth3", srcApkt, display=Ethernet),
        ("the srcApkt should broacast on eth0-->eth3 since the pktA's item was squeezed out.")
    )

    return s


scenario = test_hub()
