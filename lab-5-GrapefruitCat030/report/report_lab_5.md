# 南京大学本科生实验报告

> 课程名称：**计算机网络**           任课教师：田臣/李文中         

## 1.实验名称：Lab 5：Respond to ICMP

## 2.实验目的

在这个实验中需要完成：

- 对**面向路由器**的 ICMP Request 包进行 ICMP Reply；
- 对于一些包错误信息，如TTL expired， ARP request超时无响应等，作出相应的 ICMP ERROR 回应；
- 对于一些由**ICMP ERROR**包**引发**的上述错误，不予 Reply；但要对正常的 ICMP ERROR操作，该转发的转发。

## 3.实验内容

### 1） Responding to ICMP echo requests

在这一部分，做出对 **ICMP echo requests** 的辨析和进行 ICMP Reply：

辨析逻辑如下，以`isicmp`的枚举类型来划分**“面向路由器自身的ICMP echo requests”**：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230513000931207.png" alt="image-20230513000931207" style="zoom:80%;" />

然后就可以跳转到专门的处理部分，发包逻辑和COMMON的包逻辑基本一样，先查路由表，再查MAC（ARP处理），再进行发包/入队：

```python
# LINE 427
		elif flag == State.isicmp:
            custom_assert(isinstance(icmph, ICMP), f"isinstance({icmph}, ICMP)")
            assert(icmph.icmptype == ICMPType.EchoRequest)
            
            # If there is no match in the table, sending ICMP Unreachable pkt.
            destentry = self.router_table.LPM(dstipaddr)
            if destentry == None:
                self.icmp_errorhandle(packet, ICMPType.DestinationUnreachable, 0)
                return None
            if (packet[IPv4].ttl - 1) < 0:
                self.icmp_errorhandle(packet, ICMPType.TimeExceeded, 0)
                return None
            

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

            # Create a new Ethernet header for the NEW packet to be forwarded.
            newpacket = deepcopy(packet)

            # For ICMP data chunk
            tempdata = ICMPEchoReply()
            tempdata.data       = packet[ICMP].icmpdata.data
            tempdata.identifier = packet[ICMP].icmpdata.identifier
            tempdata.sequence   = packet[ICMP].icmpdata.sequence

            
            print(f"{next_ip} DETECT. {newpacket}")
            newpacket[Ethernet].src  = next_intf.ethaddr
            newpacket[Ethernet].dst  = next_mac
            newpacket[ICMP].icmptype = ICMPType.EchoReply           # Attention : modify the icmpType will change ICMP header code && data.
            newpacket[ICMP].icmpcode = ICMPTypeCodeMap[ICMPType.EchoReply]
            newpacket[ICMP].icmpdata = tempdata
            newpacket[IPv4].dst      = packet[IPv4].src
            newpacket[IPv4].src      = packet[IPv4].dst
            newpacket[IPv4].protocol = IPProtocol.ICMP
            newpacket[IPv4].ttl      = 33


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
```



### 2）Generating ICMP error messages

首先写一个通用的error处理函数如下：

- 传进去**引发error**的packet，引发error的type，以及error code（child type）

- 对ICMP ERROR  src packet的辨认放在起始；
- 做出error信息packet，发包逻辑同上，查表，找MAC(ARP 处理)，发包/入队；

```python
    def icmp_errorhandle(self, packet, type, childtype):
        # distinguish the icmp error packet
        icmph = packet.get_header(ICMP)
        if (icmph is not None) and \
          ((icmph.icmptype == ICMPType.DestinationUnreachable) or \
           (icmph.icmptype == ICMPType.TimeExceeded)) :
            print(f"GOOD BOY, current packet : {packet}")
            return None;
        next_ip = packet[IPv4].src
        destentry = self.router_table.LPM(next_ip)
        if destentry == None:
            return None
        if destentry.next_hop == IPv4Address('0.0.0.0'):
            next_ip = packet[IPv4].src
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

        newpacket = Ethernet() + IPv4() + ICMP()
        newpacket[Ethernet].src  = next_intf.ethaddr
        newpacket[Ethernet].dst  = next_mac
        newpacket[IPv4].src      = next_intf.ipaddr
        newpacket[IPv4].dst      = packet[IPv4].src
        newpacket[IPv4].protocol = IPProtocol.ICMP
        newpacket[IPv4].ttl      = 33
        newpacket[ICMP].icmptype = type
        newpacket[ICMP].icmpcode = childtype
        
        i = packet.get_header_index(Ethernet)
        del packet[i]
        newpacket[ICMP].icmpdata.data = packet.to_bytes()[:28]

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


        print(f"___No destentry found. Send back ICMP {packet}.___")
        return None
```

四种情况，分别为：查路由表失败，TTL expired， ARP 超时，以及Unsupported function：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230513002611469.png" alt="image-20230513002611469" style="zoom:80%;" />

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230513002509187.png" alt="image-20230513002509187" style="zoom:80%;" />

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230513002712357.png" alt="image-20230513002712357" style="zoom:80%;" />

#### **TEST结果**

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230513002851840.png" alt="image-20230513002851840" style="zoom:80%;" />

#### Deploying

TTL测试，可以看到client发送的ttl为1的ICMP，可以看到它的回复是TTL ERROR包；

![image-20230513003214991](C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230513003214991.png)

对于正常的ICMP request，正常回应：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230513004102627.png" alt="image-20230513004102627" style="zoom:80%;" />

对一个不可达的host进行ping，会因查表失败而导致ARP超时错误，产生unreachable error：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230513111912737.png" alt="image-20230513111912737" style="zoom:80%;" />

可以看到error code 是属于ARP超时的host unreachable：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230513112028678.png" alt="image-20230513112028678" style="zoom:80%;" />

server1到client的traceroute输出如下，可以看到server1不断发TTL递增的UDP包：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230513112727884.png" alt="image-20230513112727884" style="zoom:80%;" />

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230513113625335.png" alt="image-20230513113625335" style="zoom:80%;" />