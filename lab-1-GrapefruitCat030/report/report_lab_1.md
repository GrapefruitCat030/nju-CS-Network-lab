# 南京大学本科生实验报告

> 课程名称：**计算机网络**           任课教师：田臣/李文中         

## 1.实验名称：Lab 1: Switchyard & Mininet

## 2.实验目的

了解mininet，wireshark，通过阅读switchyard文档认识switchyard，在一些基本操作中巩固对实验工具的认知。

## 3.实验内容

### 1)Modify the Mininet topology

> option2：create a different topology containing 6 nodes using hosts and hubs (don't use other kinds of devices).

将网络拓扑修改为六个节点：一个`hub`，一个`CLI`，四个`server`。具体代码实现（修改后）：

```python
nodes = {
    "server1": {
        "mac": "10:00:00:00:00:{:02x}",
        "ip": "192.168.100.1/24"
    },
    "server2": {
        "mac": "20:00:00:00:00:{:02x}",
        "ip": "192.168.100.2/24"
    },
    "server3": {
        "mac": "30:00:00:00:00:{:02x}",
        "ip": "192.168.100.3/24"
    },
    "server4": {
        "mac": "40:00:00:00:00:{:02x}",
        "ip": "192.168.100.4/24"
    },
    "client": {
        "mac": "50:00:00:00:00:{:02x}",
        "ip": "192.168.100.5/24"
    },
    "hub": {
        "mac": "60:00:00:00:00:{:02x}",
    }
}
```

### 2)Modify the logic of a device

> Your task is to count how many packets have passed through a hub in and out. You need to record the statistical result every time you receive one packet with the format of each line `in:<ingress packet count> out:<egress packet count>`.

我们只需要在代码中用两个变量记录packet出入数即可：

```python
        else:
            incount = 1			# record the incount, always be 1
            outcount = 0 		# record the outcount, decided by the interfaces except the ingress
            for intf in my_interfaces:
                if fromIface!= intf.name:
                    log_info (f"Flooding packet {packet} to {intf.name}")
                    net.send_packet(intf, packet)
                    outcount += 1
            log_info(f"in: {incount} out: {outcount}")	# log the info
```

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230321225254210.png" alt="image-20230321225254210" style="zoom:80%;" />

### 3)Modify the test scenario of a device

> option1：Create one test case by using the given function `new_packet` with different arguments.

阅读手册知道test的expect事件有三种： `PacketInputEvent`, `PacketInputTimeoutEvent`, 和 `PacketOutputEvent`。在这里用`new_packet`创建一个新的数据包，并添加两个expect事件： `PacketInputEvent` 和 `PacketOutputEvent`。

```python
    # test case 4: a frame with any unicast address except one assigned to hub
    # interface should be sent out all ports except ingress
    testpkt = new_packet(
        "ef:60:00:00:00:05",
        "aa:bb:cc:dd:ee:ff",
        "1.2.3.4",
        "5.6.7.8"
    )
    s.expect(
        PacketInputEvent("eth2", testpkt, display=Ethernet),
        ("An Ethernet frame with a broadcast destination address "
         "should arrive on eth2")
    )
    s.expect(
        PacketOutputEvent("eth0", testpkt, "eth1", testpkt, display=Ethernet),
        ("The Ethernet frame with a broadcast destination address should be "
         "forwarded out ports eth0 and eth1")
    )
```

运行测试结果如下：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230321231852178.png" alt="image-20230321231852178" style="zoom:80%;" />

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230321231904555.png" alt="image-20230321231904555" style="zoom:80%;" />

### 4)Run your device in Mininet

我们将修改实现的`myhub`放到Mininet上面试试看：

- 先用`sudo python start_mininet.py `运行修改后的`start_mininet`，得到一个虚拟网络拓扑；

  <img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230321222959568.png" alt="image-20230321222959568" style="zoom:80%;" />

- 然后在`hub`节点用xterm打开，并在虚拟环境下运行myhub.py，堵塞原本的hub并用实现myhub代替：

  - 首先`mininet> hub xterm &`

  - 然后`syenv`进入虚拟环境（这里alias了一下）

    <img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230321232444211.png" alt="image-20230321232444211" style="zoom:80%;" />

  - 运行`myhub.py`：

    <img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230321232533583.png" alt="image-20230321232533583" style="zoom:80%;" />

  - 在mininet中进行`pingall`，查看结果：

    <img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230321232634789.png" alt="image-20230321232634789" style="zoom:80%;" />

- 可以观测到五个host成功通信的，hub则因节点特性不进行通信。

### 5)Capture using Wireshark

选取`server1`为目标host进行抓包，端口为server1-eth0。在step4的前提条件下，在mininet上使用`client ping -c 1 server1`命令，共抓取到达server1-eth0端口的包6个：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230321234918121.png" alt="image-20230321234918121" style="zoom:80%;" />

对这些包进行分析：

- 第1、2个包为进行网关状态检测而分别从client发出和从server1返回的数据包；

  > ping 命令会向指定的网络主机发送特殊网络数据报 IMCP ECHO_REQUEST。多数网络设备收到该数据包后会做出回应，通过此法即可验证网络连接是否正常。
  >
  > 有时从安全角度出发，通常会配置部分网络通信设备以忽略 ICMP 数据包，因为这样可以降低主机遭受潜在攻击者攻击的可能性。当然，防火墙经常被设置为阻碍 IMCP 通信。

  （由手册可知，myhub的运行把防火墙暂时关闭了）

- 第3、4、5、6个包为ARP报文，用以解析目标IP地址

  - 3、5为ARP请求报文，分别从client和server1向对方发出请求；
  - 4、6为ARP响应报文，分别从client和server1向对方发出响应（带着解析好的IP地址）

## 4.实验结果

实验结果同实验过程。

## 5.核心代码

- `start_mininet.py`

  - ```python
    nodes = {
        "server1": {
            "mac": "10:00:00:00:00:{:02x}",
            "ip": "192.168.100.1/24"
        },
        "server2": {
            "mac": "20:00:00:00:00:{:02x}",
            "ip": "192.168.100.2/24"
        },
        "server3": {
            "mac": "30:00:00:00:00:{:02x}",
            "ip": "192.168.100.3/24"
        },
        "server4": {
            "mac": "40:00:00:00:00:{:02x}",
            "ip": "192.168.100.4/24"
        },
        "client": {
            "mac": "50:00:00:00:00:{:02x}",
            "ip": "192.168.100.5/24"
        },
        "hub": {
            "mac": "60:00:00:00:00:{:02x}",
        }
    }
    ```

-  `myhub.py`

  - ```python
            else:
                incount = 1			# record the incount, always be 1
                outcount = 0 		# record the outcount, decided by the interfaces except the ingress
                for intf in my_interfaces:
                    if fromIface!= intf.name:
                        log_info (f"Flooding packet {packet} to {intf.name}")
                        net.send_packet(intf, packet)
                        outcount += 1
                log_info(f"in: {incount} out: {outcount}")	# log the info
    ```

- `testcases/myhub_testscenario.py`

  - ```python
        # test case 4: a frame with any unicast address except one assigned to hub
        # interface should be sent out all ports except ingress
        testpkt = new_packet(
            "ef:60:00:00:00:05",
            "aa:bb:cc:dd:ee:ff",
            "1.2.3.4",
            "5.6.7.8"
        )
        s.expect(
            PacketInputEvent("eth2", testpkt, display=Ethernet),
            ("An Ethernet frame with a broadcast destination address "
             "should arrive on eth2")
        )
        s.expect(
            PacketOutputEvent("eth0", testpkt, "eth1", testpkt, display=Ethernet),
            ("The Ethernet frame with a broadcast destination address should be "
             "forwarded out ports eth0 and eth1")
        )
    ```

  

## 6.总结与感想

- 搞清楚了mininet和switchyard的关系（switchyard用代码实现网络组件，可以代替真实的网络组件）
- 读了switchyard手册，基本搞懂了在测试环境和真实环境下switchyard的运行流程；
