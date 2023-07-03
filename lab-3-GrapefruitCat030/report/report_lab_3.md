# 南京大学本科生实验报告

> 课程名称：**计算机网络**           任课教师：田臣/李文中         

## 1.实验名称：Lab 3：Respond to ARP

## 2.实验目的

在接下来三个实验，一步步实现router。lab3为第一步：实现ARP包的接收和回应。

## 3.实验内容

### 1）handle ARP packet

在这一步，需要实现对ARP包的接收，以及检查ARP包的目的ip是否为当前router中的一个接口，是则返回一个ARP的response，否则将这个ARP request丢弃。

#### CODE

代码的实现逻辑为：

1. 先判断接收到的packet是否为ARP，不是则丢弃；
2. 若为ARP，则进一步对Ethernet首部进行判断；如果eth destination不是广播地址或者不是当前入端口MAC，则丢弃；然后在router的接口中寻找与ARP目的IP地址相同的接口；
3. 若找不到，则丢弃；找到则进行processing. 构建一个ARP response，将response从抓获的接口发送回去（`there is a possible case that ARP requests interface B but captured by interface A. `）

代码如下：

```py
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

                # Hoding a ARP request, prepare to forward the ARP reply.
                if arp.operation == ArpOperation.Request: 
                    # make a ARP respond through proper interface.
                    rpacket = create_ip_arp_reply(intf.ethaddr, arp.senderhwaddr, arp.targetprotoaddr, arp.senderprotoaddr)

                    # there is a possible case that ARP requested interface B but captured by interface A. 
                    self.net.send_packet(captureIntf, rpacket)
                    log_info(f"****The packet __{rpacket}__ is sent by {ifaceName}.")
                    return 0
        log_info("____Haha, there is no relative intf.____")
```

#### **TEST**

测试结果如下：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230412220513143.png" alt="image-20230412220513143" style="zoom:50%;" />

#### DEPLOY

如图，router成功实现了对ARP包的respond，但不对ICMP进行respond。

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230412221202903.png" alt="image-20230412221202903" style="zoom:80%;" />

检查respond的ARP包格式，正确：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230412221349842.png" alt="image-20230412221349842" style="zoom:80%;" />

好的，现在来看server1和server2的表现：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230412221634069.png" alt="image-20230412221634069" style="zoom:80%;" />

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230412221749120.png" alt="image-20230412221749120" style="zoom:80%;" />

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230412221919304.png" alt="image-20230412221919304" style="zoom:80%;" />

检查确定router对ARP request准确进行了respond。

### 2）ARP Cache

在这一阶段我们需要实现一个类似于交换机自学习表一样的ARP缓存表。这个缓存表自学习src方ARP的ip和mac，将两者聚合成一个表项加入缓存表。在这个缓存表还加入了timeout机制，在这里表项的TTL为100s。

#### CODE

代码实现和switch的to机制差不多：第一个代码块是cache的类，第二个是在arp处理过程中的entry更新。

```py
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
```

更新的过程包括：

1. 如果ARP是指向router的，才进行对cache的操作；
2. 检查cache中有无此ARP的src IP， 没有则进行学习；
3. 如果存在src IP，则检查entry中的MAC是否和src MAC相同，不同则进行更新；

```py
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
```



#### TEST

下图是cache的更新过程。可以看出，因为样例只有两个指向router的ARP request， 所以表项只增加了两项：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230412235221790.png" alt="image-20230412235221790" style="zoom:80%;" />