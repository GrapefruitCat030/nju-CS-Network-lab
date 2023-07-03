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
        PacketOutputEvent("eth0", testpkt, "eth2", testpkt, display=Ethernet),
        ("The Ethernet frame with a broadcast destination address should be "
         "forwarded out ports eth0 and eth2")
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
        PacketOutputEvent("eth1", reqpkt, "eth2", reqpkt, display=Ethernet),
        ("Ethernet frame destined for 30:00:00:00:00:33 should be flooded out"
         " eth1 and eth2")
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

    # # test case 4: 10s time test
    
    # # time.sleep(10)

    # testpkt = new_packet(
    #     "20:00:00:00:00:01",
    #     "30:00:00:00:00:33",
    #     '192.168.1.100',
    #     '172.16.42.33'
    # )
    # s.expect(
    #     PacketInputTimeoutEvent(10.0),
    #     ("stop for 10 seconds, hence cleaning the switch table.")
    # )    
    # s.expect(
    #     PacketInputEvent("eth0", testpkt, display=Ethernet),
    #     ("An Ethernet frame with a broadcast destination address "
    #      "should arrive on eth0")
    # )
    # s.expect(
    #     PacketOutputEvent("eth1", testpkt, "eth2", testpkt, display=Ethernet),
    #     ("The Ethernet frame with a broadcast destination address should be "
    #      "forwarded out ports eth1 and eth2")
    # )

    return s


scenario = test_hub()
