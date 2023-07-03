# 南京大学本科生实验报告

> 课程名称：**计算机网络**           任课教师：田臣/李文中          

## 1.实验名称：Lab 2：Learning Switch

## 2.实验目的

通过实验学习switch在LAN中的机制，包括自学习机制，以及自学习过程中对timeout表项的处理、使用的LRU算法、流控机制。

## 3.实验内容

每个阶段的实验都分为CODE, TEST, DEPLOY三个环节。

### 1)Basic Switch

在这一阶段，我们完成switch的最基础的机制：自学习机制。在这一阶段switch的table容量是无限的，来多少学多少。

#### CODE

coding如下，用一个 `SWITCH_CHART` 类把switch的功能抽象出来。其中`SWChart`是一个`dict`，作为switch table用来存储学习表项（`mac--intf`键值对）；学习接收到的packet的过程封装成一个`addItem`函数，`getIntf`函数则是用来在forwarding时获取dest MAC相应的egress。

```python
# MAC && interface
class SWITCH_CHART(object):
    def __init__(self):
        # a dict for recording mac-intf couples.
        self.SWChart = {}

    def addItem(self, mac, intf):
        assert ((mac in self.SWChart) == False)
        self.SWChart[mac] = intf
        log_info(f"the chart add a couple: {mac} --- {intf}")

    def getIntf(self, mac):
        assert ((mac in self.SWChart)== True)
        return self.SWChart[mac]
```

packet进入switch和forward的逻辑如下，即蓝框就是主要的自学习机制逻辑；

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402173218609.png" alt="image-20230402173218609" style="zoom: 80%;" />

#### TEST

自己写了一个base switch的test scenario：（1，2）先用一个broadcast的packet进行一次学习，顺带检查flooding是否出错；（3，4，5，6）然后用一个unicast的request packet再进行一次学习，回复的respond packet在自学习机制下，应该为unicast而不是broadcast；（7，8）然后将3中同一个MAC的host的ingress更改进行测试。

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402173602603.png" alt="image-20230402173602603" style="zoom: 80%;" />

#### DEPLOY

我们将switch部署到mininet上面，来看看实际效果：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402175916473.png" alt="image-20230402175916473" style="zoom:80%;" />

我们只用一次ping就可以看出自学习机制的威力：client首先为了得到server1的MAC地址，broadcast一个ARP的packet，这意味着switch的table里面多了一个 （CLI-MAC，CLI-port）的表项；然后server1进行ARP的response，该packet到达switch时找到这个表项，只对CLI-port进行forwarding——从图可知，server2此时已经无法再收到server1的response ARP，说明自学习机制已经起了作用；同时response ARP为switch table增加了一个（S2-MAC, S2-port）的表项，后面紧随着的CLI发出的ICMP报文同理没有flooding到server2中。 

### 2)Timeout Mechanism

在这一阶段，我们在base的基础上加上一个time out的处理机制：把留在switch table中的超过了一定时间范围的表项去掉。

#### CODE

在to机制的实现中，table依然用一个`dict`来存储；但表项的格式变为（MAC，ENTRY），其中`ENTRY`为一个类，包括了MAC对应的interface和elapsed time；另外对elapsed time也做了一个`elpTime`类的封装。所以一个表项的结构底层为：

```
(MAC, (MAC, interface， elpsTime) )
```

`elpsTime`在初始化的时候使用了`time`库的`time()`函数来读取当前系统时间，实例成员`stamp`用来给`ENTRY`类调用`getstamp()`时使用，将存在时长写入当前表项；而`getstamp()`在`SWITCH_CHART`中又被函数`get_Time()`和`updateItems()`使用，`get_Time()`这个函数是table层次的抽象，用来获取当前表项的存在时长；`updateItems()`这个函数是一个对switch table进行更新的封装（*里面对表项进行遍历并做了存在时长与类成员glbTimestamp的比较*）。

除此之外，`SWITCH_CHART.AaddItem`是对table写入新表项的一个封装；`SWITCH_CHART.setTime2zero`则是将表项中的elpsTime重新设置为0.

```python
class elpsTime(object):
    def __init__(self):
        self.begin = time.time()
        self.stamp = 0
    
    def __str__(self):
        return str.format("(begin:{}, stamp:{})", self.begin, self.stamp)

class ENTRY(object):
    def __init__(self, mac, intf, elpstime):
        self.mac = mac
        self.intf = intf
        self.elpstime = elpstime

    def __str__(self):
        return str.format("ENTRY: mac:{},intf{},elpstime:{}", self.mac, self.intf, self.elpstime)

    def getstamp(self):
        self.elpstime.stamp = time.time() - self.elpstime.begin
        return self.elpstime.stamp

    def restart(self):
        self.elpstime.begin = time.time()
        self.elpstime.stamp = 0

# MAC && interface
class SWITCH_CHART(object):

    # the longest time a table item live.
    glbTimestamp = 10

    def __init__(self):
        # a dict for recording mac-intf couples.
        self.SWChart = {}

    def addItem(self, mac, intf):
        assert ((mac in self.SWChart) == False)
        # mac--[interface, elapsed_time]
        elapsed_time = elpsTime()
        entry = ENTRY(mac, intf, elapsed_time)
        self.SWChart[mac] = entry
        log_info(f"****The chart add an {entry}.")

    def get_Intf(self, mac):
        if not (mac in self.SWChart):
            return False
        assert ((mac in self.SWChart) == True)
        return self.SWChart[mac].intf

    def changeIntf(self, mac, intf):
        oldintf = self.SWChart[mac].intf
        self.SWChart[mac].intf = intf
        log_info(f"****Now the src mac:{mac} intf has been changed from {oldintf} into {intf}.")

    def get_Time(self, mac):
        assert ((mac in self.SWChart) == True)
        return self.SWChart[mac].getstamp()
    
    def setTime2zero(self, mac):
        oldtime = self.SWChart[mac].elpstime
        self.SWChart[mac].restart()
        log_info(f"****Now the src mac:{mac} time has been set from {oldtime} into {self.SWChart[mac].elpstime}.")

    def updateItems(self):
        for key in list(self.SWChart.keys()):
            temp = self.SWChart[key].getstamp()
            if temp > self.glbTimestamp:
                del self.SWChart[key]
```

在switch中接收packet并转发的流程code如下：（圈出来的是to机制新增）可以看到是每次**收到**packet后才进行table的检查更新。

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402213654773.png" alt="image-20230402213654773" style="zoom:80%;" />

#### TEST

这是lab给的编译后的to机制的test scenario测试结果：

<img src="C:/Users/11342/Pictures/networklab/Snipaste_2023-03-24_19-56-38.png" alt="Snipaste_2023-03-24_19-56-38" style="zoom:80%;" />

<img src="C:/Users/11342/Pictures/networklab/Snipaste_2023-03-24_19-56-52.png" alt="Snipaste_2023-03-24_19-56-52" style="zoom:80%;" />

自己也写了一个，在base的test基础上加了一个to的样例：（前面的样例是和base一样的）

```python
    # test case 4: 10s time test
    testpkt = new_packet(
        "20:00:00:00:00:01",
        "30:00:00:00:00:33",
        '192.168.1.100',
        '172.16.42.33'
    )
    s.expect(
        PacketInputTimeoutEvent(10.0),
        ("stop for 10 seconds, hence cleaning the switch table.")
    )    
    s.expect(
        PacketInputEvent("eth0", testpkt, display=Ethernet),
        ("An Ethernet frame with a broadcast destination address "
         "should arrive on eth0")
    )
    s.expect(
        PacketOutputEvent("eth1", testpkt, "eth2", testpkt, display=Ethernet),
        ("The Ethernet frame with a broadcast destination address should be "
         "forwarded out ports eth1 and eth2")
    )
```

测试结果如下：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402214335950.png" alt="image-20230402214335950" style="zoom:80%;" />

#### DEPLOY

我们给出的最长表项TTL是10s。要在mininet上验证这个假设，我们可以：

- ①先用CLI对server1发起一次ping，让switch从ICMP和ARP包中进行自学习；
- ②然后再过10s后从server1发起对CLI的ping——
- ③如果to机制正确实现，那么会出现**flooding**的情况。下面是结果展示：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402214909764.png" alt="image-20230402214909764" style="zoom: 80%;" />

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402214945267.png" alt="image-20230402214945267" style="zoom:80%;" />

第一次ping过后，switch收了6个packet，table里面应有的表项为：

| MAC        | PORT |
| ---------- | ---- |
| CLI 30::01 | eth2 |
| S1 10::01  | eth0 |

后面的两个packet因为是在6s时收到的，所以不会引起flooding；那么现在我们再试试：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402215431007.png" alt="image-20230402215431007" style="zoom:80%;" />

在server2收到的server1发往CLI的ICMP包说明flooding现象出现了，意味着原本的表项已被清除。

### 3)Least Recently Used（LRU）

在这一阶段我们要在base的基础实现上添加LRU机制，同时将table的容量限制为5.

#### CODE

对LRU机制的实现，为了不用每次更新table时都使用笨比遍历，使用了哈希+双向链表的数据结构。哈希表用`dict`来实现，存储的是（MAC，NODE）键值对——`NODE`为switch表项，它是一个双向链表节点，里面的数据包括了MAC和interface；用哈希+双向链表实现的好处就是：

- 在查找MAC对应的port时，直接从哈希表进行O(1)的查找，找到对应的node，然后就可以获取port；
- 在每次**剔除**LRU的表项时，仅仅需要从链表尾部进行节点的删除，这是一个O(1)的操作；而在**加入**新学习进来的表项时，也仅仅需要从链表头部进行节点的插入，也是一个O(1)的操作；
- 在更新已有表项（把它变成MRU）时，只需要先用哈希找到对应node，然后对node进行一次删除和重新插入的操作，也是O(1)。

code如下：

```python
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
```

在switch中接收packet并转发的流程code如下：（圈出来的是LRU机制新增，顺便把base写的答辩封装改舒服了一点点）

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402221943865.png" alt="image-20230402221943865" style="zoom:80%;" />

#### TEST

这是lab给的编译后的LRU机制的test scenario测试结果：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402222532190.png" alt="image-20230402222532190" style="zoom:80%;" />

自己也写了个，样例思想是用六个host轮流发包填满LRU机制的table，顺带挤出LRU的表项；然后用一个host对被挤出的表项中的MAC进行发包，检查有无flooding——flooding则实现正确。文件放在`testcase/`中。

#### DEPLOY

因为表项容量为5的话，在只有3个host中的mininet是无法体现出LRU机制的。所以暂且将表项数量改为2，进行deploy测试。

思想为：先用CLI对server1进行ping，此时会由于ARP和ICMP包的接收，table里面的表项将会为`CLI-eth2`和`server1-eth0`，根据LRU机制，在链表尾部的应为`CLI-eth2`；此时用server2对CLI进行ping，将LRU的表项`CLI-eth2`剔除，加入新的`server2-eth1`表项，然后在一系列的收包过程后，最终又只剩下S2和CLI的表项；再进行一次server2向server1的ping，server1会因为ARP进行respond，观测此时是否有flooding现象的产生——有flooding则表明实现正确。

过程如下：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402223831493.png" alt="image-20230402223831493" style="zoom:80%;" />

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402223906106.png" alt="image-20230402223906106" style="zoom: 80%;" />

此时switch中的表项为：即`CLI-eth2`为LRU表项

| MAC        | PORT | LRU  |
| ---------- | ---- | ---- |
| CLI 30::01 | eth2 | 1    |
| S1 10::01  | eth0 | 0    |

接下来使用server2对CLI进行ping：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402224936079.png" alt="image-20230402224936079" style="zoom:80%;" />

根据抓包推断，原本就只有两个表项且S1的表项为LRU，所以把它先挤出去，S2为MRU；然后后面的包都只有CLI和S2两个地址，直接看最后一个包的dest，为CLI，所以S2表项为LRU；现在的表项应为：

| MAC        | PORT | LRU  |
| ---------- | ---- | ---- |
| CLI 30::01 | eth2 | 0    |
| S2 20::01  | eth1 | 1    |

再进行一次server2向server1的ping，观测来自S1的ARP response产生了flooding，说明表项中确实没有S1的表项了，实现正确。

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402230412654.png" alt="image-20230402230412654" style="zoom:80%;" />

### 4)Least Traffic Volume（LTV）

在这一阶段我们要在base的基础实现上添加LTV机制，同时将table的容量限制为5.

#### CODE

在LTV的实现中，因为每次表满时自学习要删除一个LTV的表项，即找出**最小**traffic的port表项删除；为了不使用笨比遍历，用一个**哈希+堆**的数据结构来实现LTV机制。（使用了python的heapq库来构造堆）

code如下，表项采用了一个（MAC, ENTRY）的结构，其中ENTRY结构为（MAC, interface， volume）。哈希表的使用可以方便用O(1)时间来找到MAC对应的ENTRY，而堆的结构保证了每次自学习插入表项后，堆顶都是LTV的表项，方便O(1)时间弹出。结合switch过程来看，最重要的封装是`SWITCH_CHART.addItem`和`SWITCH_CHART.updateLTV`，起到了LTV机制的实现。

```python
class ENTRY(object):
    def __init__(self, mac, intf, volume):
        self.mac = mac
        self.intf = intf
        self.volume = volume
    
    def __str__(self):
        return str.format("Entry: mac:{}, intf:{}, volume:{}", self.mac, self.intf, self.volume)

    def __lt__(self, other):
        return self.volume < other.volume
    
    def __gt__(self, other):
        return other.__lt__(self)
    
    def __eq__(self, other):
        return self.volume == other.volume
    
    def __ne__(self, other):
        return not self.__eq__(other)


# Use a more efficient implementation of Traffic Control (LTV) algorithm ----- Min Heap
# the structure of Hashmap is: (mac, ENTRY), among it the ENTRY'structure is [mac, intf, volume]
# MAC && interface
class SWITCH_CHART(object):

    def __init__(self, capacity):
        # a dict(hashMap) and a DLL for recording mac-intf couples.
		# capacity: the maximum number of items
        self.capacity = capacity
        self.SWmap = {}
        self.SWheap = []
        self.count = 0

    def addItem(self, mac, intf):
        assert ((mac in self.SWmap) == False)

        node = ENTRY(mac, intf, 0)
        self.SWmap[mac] = node
        if self.count < self.capacity:
            self.count += 1
            heapq.heappush(self.SWheap, node) 
            log_info(f"****The chart is not full.Add an {node}, NOW count is {self.count}.")
        else:
            oldestnode = self.SWheap[0]     # get the lowest volume entry
            heapq.heappop(self.SWheap)      # and then delete it from Hashmap and heap.
            del self.SWmap[oldestnode.mac]

            heapq.heappush(self.SWheap, node) 
            log_info(f"****Full chart!! delete old {oldestnode}, add an new {node}. NOW count is {self.count}")
            for n in self.SWheap:
                print("    the table item: {}", n)
            print("\n")

    def changeIntf(self, mac, intf):
        oldnode = self.SWmap[mac]
        self.SWmap[mac].intf = intf
        log_info(f"****Now the src mac:{mac} intf has been changed from {oldnode} into {self.SWmap[mac]}.")

    def getIntf(self, mac):
        if not (mac in self.SWmap):
            return False
        assert ((mac in self.SWmap) == True)
        return self.SWmap[mac].intf

    def updateLTV(self, mac):
        assert ((mac in self.SWmap) == True)
        node = self.SWmap[mac]
        node.volume += 1
        heapq.heapify(self.SWheap) 
```

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230402231612368.png" alt="image-20230402231612368" style="zoom:80%;" />

#### TEST

这是lab给的编译后的LTV机制的test scenario测试结果：

![Snipaste_2023-03-28_17-39-52](C:/Users/11342/Pictures/networklab/Snipaste_2023-03-28_17-39-52.png)

#### DEPLOY

和LRU机制差不多，把表项数量改为2进行deploy测试。

思想和LRU的deploy差不多，先把表填满，然后用第三个host挤出LTV表项，



<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230403001645987.png" alt="image-20230403001645987" style="zoom:80%;" />

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230403001712216.png" alt="image-20230403001712216" style="zoom:80%;" />

此时switch中的表项为：即`S1-eth0`为LTV表项

| MAC        | PORT | traffic     |
| ---------- | ---- | ----------- |
| CLI 30::01 | eth2 | 3           |
| S1 10::01  | eth0 | 2 (**LTV**) |

此时用CLI对server2进行ping，按照LTV机制，CLI进行ARP广播，server2返回的ARP response会把LTV表项给挤掉，过程不会出现flooding；

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230403002722999.png" alt="image-20230403002722999" style="zoom:80%;" />

此时switch中的表项为：即`CLI-eth2`为LRU表项

| MAC        | PORT | traffic     |
| ---------- | ---- | ----------- |
| CLI 30::01 | eth2 | 6           |
| S2 20::01  | eth1 | 2 (**LTV**) |

此时用CLI对server1进行ping，从CLI发出的ICMP需要产生flooding才证明实现正确（表项中没有server1）；

![image-20230403003103861](C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230403003103861.png)

证明表项中没有S1，LTV实现正确。