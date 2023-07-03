# 南京大学本科生实验报告

> 课程名称：**计算机网络**           任课教师：田臣/李文中         

## 1.实验名称：Lab 6：Reliable Communication

## 2.实验目的

实验中由三个部分：`blaster`，`middlebox`和`blastee`组成。实验中需要保证从blaster经middlebox到blastee的可靠传输。

在这个实验中需要完成：

- 对`middlebox`，实现简单的路由功能，包括修改header中的信息，找到相应port进行转发；

- 对`blastee`，实现一个ACK机制，收到blaster的包后回复ACK packet；
- 对`blaster`，实现一个发包的sliding window机制，同时实现ACK超时选择重传.

## 3.实验内容

### 1） Middlebox

代码如下。在middlebox中分别对两个port收到的包进行处理：

- *blaster->blastee*：根据给出的drop几率发生丢包，此处使用了random库；无丢包则将blastee信息以及发端口信息填上packet，将其转发出去；
- *blastee->blaster*：由blastee发过来的包一定为ACK包，不进行drop，填好信息转发；

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230522165035316.png" alt="image-20230522165035316" style="zoom:80%;" />



### 2）Blastee

代码如下。要构造一个ACK包，就包括了 `ETH Hdr` |  `IP Hdr`  |  `UDP Hdr` | `RAW Hdr` 四个字段。将前三个字段信息填写好后，根据给出的raw bytes标准对`RAW Hdr`进行填写，填入的信息从收到的packet上拿取，收到的packet格式由blaster规定。

填入的信息包括：

- *rawseqnumb*：packet的序号，用作ACK确定号；

- *rawpayload*：收到的packet中有效payload的前八个字节；

> rawlength整数使用了struct库中的unpack，对大端序字节序列unpack得出。

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230522165448957.png" alt="image-20230522165448957" style="zoom:80%;" />

### 3）Blaster

首先是blaster的成员变量，有着不同的功能划分，从上到下分别作用为：

- 传进blaster的参数，用来实现下面的机制；
- 超时中断处理变量，若产生超时，则关闭超时trap，发包只会发出重传包，发完再把trap打开（不会影响收ACK）
- ACK和重传机制使用的ACK确定数组，重传packet数组，重传区间*[retranorient, retranend]*
- 滑动窗口指针
- blaster性能测量用的变量

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230522171256989.png" alt="image-20230522171256989" style="zoom:80%;" />

#### 滑动窗口机制

在没有收到ACK时，blaster会检查超时中断和窗口长度，若没有超时，并且窗口长度未满，即进行发包，并移动窗口右端RHS直到窗口长度达到最长。packet构建根据lab手册中给出的字段标准构建。

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230522171623544.png" alt="image-20230522171623544" style="zoom:80%;" />

一旦收到ACK，blaster对ACK序号进行检查，如果等于当前LHS，就将窗口向前移动：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230522171859678.png" alt="image-20230522171859678" style="zoom:80%;" />

#### 超时重传机制

blaster使用了一个定时器来检查超时，当没有packet到达时都会进行一次检查，若超时，则将trap关掉，设置好重传区间，准备进入重传处理：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230522172323184.png" alt="image-20230522172323184" style="zoom:80%;" />

每次recv间隔都只进行一次重传，直到对重传区间遍历完毕，全部需要重传的packet发出，才重新把trap打开，可以进入正常发包：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230522172518963.png" alt="image-20230522172518963" style="zoom:80%;" />

#### 性能测量

在接收到第num个ACK时，进行一次性能数据的输出：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230522172755088.png" alt="image-20230522172755088" style="zoom:80%;" />

在mininet上输出结果如下：

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230522172817854.png" alt="image-20230522172817854" style="zoom:80%;" />

可以看到100个packet测量结果近20s输出一次，throughput基本在700B左右，而goodput在400B左右。

### 抓包结果

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230522174126877.png" alt="image-20230522174126877" style="zoom:80%;" />

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230522174202406.png" alt="image-20230522174202406" style="zoom:80%;" />

<img src="C:/Users/11342/AppData/Roaming/Typora/typora-user-images/image-20230522174311176.png" alt="image-20230522174311176" style="zoom:80%;" />

根据抓包结果，对发出的packet以及收到的ACK中的raw header字段进行解析，可以看出滑动窗口正确运行。（图片中只是举例）