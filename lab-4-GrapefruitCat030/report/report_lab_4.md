# 南京大学本科生实验报告

> 课程名称：**计算机网络**           任课教师：田臣/李文中         

## 1.实验名称：Lab 4：Forwarding Packets

## 2.实验目的

接收和转发到达链路并发往其他主机的数据包。转发过程的一部分是在转发表中执行“最长前缀匹配”地址查找。

对没有已知以太网 MAC 地址的 IP 地址发出 ARP 请求。路由器通常必须将数据包发送到其他主机，并且需要以太网 MAC 地址才能执行此操作。

## 3.实验内容

### 1） IP Forwarding Table Lookup

使用的LPM算法如下：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230505083326003.png" alt="image-20230505083326003" style="zoom:80%;" />

### 2）Send ARP Request and Forward PacketSend ARP Request and Forward Packet

总体的逻辑为：

```
                         +---------------------+
                         |   queue processing  |
                         +----------+----------+
                                    |
                         +----------v----------+
                         |    receive packet   |
                         +----------+----------+
                                    |
               arp        +---------v---------+
          +---------------+   handle packet   |
          |               +---------+---------+
          |                         |
          v                         | common
  +-------+--------+                |
  |                |     +----------v------------+
  | arp operation  |     | LPM                   |
  |                |     | get next-IP next-intf |
  +----------------+     +----------+------------+
                                    |
                                    |
                         +----------v------------+
            MAC founded  |search next-MAC in cache
        +----------------+according to next-IP   |
        |                +----------+------------+
        |                           |
        |                           |
        |                           v
+-------+-----------+    +----------+------------+
|                   |    | make arp query        |
| make a new packet,|    | to search the next-MAC
| send it directly  |    |                       |
|                   |    |                       |
+-------------------+    +-----------------------+
```

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230505084418386.png" alt="image-20230505084418386" style="zoom: 80%;" />

对于make ARP query逻辑为：

```
+----------------------------+
|look up queue if there      |          yes
|is a query item for next-IP | +-----------------------+
+------------+---------------+                         |
             | no                                      |
             |                                         |
+------------v-------------------+                     |
|make an ARP request for next-IP,|                     |
|src is next-Intf's IP and MAC   |                     |
+------------+-------------------+                     |
             |                                         |
             |                                         |
+------------v---------------------+                   |
|make a packet missing next-MAC,   |                   |
|It is the same as other places of | <-----------------+
|the package recei^ed.             |
+------------+---------------------+
             |
+------------v---------------------+
|                                  |
| push the packet missing next-MAC |
| in queue, for futurn resolving   |
|                                  |
|                                  |
+----------------------------------+
```

request队列为一个`dict`，item的表示为一个`next-IP`字符串和`ARP_2b_REPLY`类构建的实例构成的键值对，详见代码；

request队列处理逻辑为：

```
      +--------------------+
      | fix the state first|
      | for judging        |
      +---------+----------+
                |
                |
                |
      +---------v----------+                            +----------------------------------+
      |iterate whole queue |   if cache sa^ed next-MAC  |   stuff the next-MAC             |
      |for single item:    +--------------------------->+   to the packet to be resolved   |
      +---------+----------+                            |                                  |
                |                                       +----------------+-----------------+
                |                                                        |
                | else                                  +----------------v-----------------+
                |                                       |  send all packet in the item list|
                |                                       |  and delete the item             |
                |                                       |                                  |
                v                                       +----------------------------------+
     +----------+-----------+
     | check item if timeout|
     +----------+-----------+
                |
                |
  +-------------+--------------+
  |                            | retransmition less than 5
  v retransmition abo^e 5      v but current request time out
+-+---------------------+   +--+---------------------------+
|                       |   |                              |
| delete the item       |   |  reetransmit arp request     |
+-----------------------+   |  and add 1 to record it      |
                            |                              |
                            |                              |
                            |                              |
                            +------------------------------+
```

部分代码展示：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230505090536983.png" alt="image-20230505090536983" style="zoom:80%;" />

#### **TEST结果**

<img src="Snipaste_2023-05-05_00-29-52.png" alt="Snipaste_2023-05-05_00-29-52" style="zoom:80%;" />

<img src="Snipaste_2023-05-05_00-30-16.png" alt="Snipaste_2023-05-05_00-30-16" style="zoom:80%;" />

#### Deploying

手册上的测试结果：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230505091514976.png" alt="image-20230505091514976" style="zoom:80%;" />

可以看到server1成功收到了所有的包并且没有影响到server2：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230505091752488.png" alt="image-20230505091752488" style="zoom: 80%;" />

也能成功ping通server2：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230505091855752.png" alt="image-20230505091855752" style="zoom:80%;" />

server1和server2分别ping向client：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230505092032151.png" alt="image-20230505092032151" style="zoom:80%;" />

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230505092059202.png" alt="image-20230505092059202" style="zoom:80%;" />