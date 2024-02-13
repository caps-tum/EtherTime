
# Spend some Time on Time / It is Time to Talk about Time
_Vincent Bode, Arpan Gujarati_

### Motivation

"Time is of the essence", to many readers this might only be an idiom but the relevance of time is so ubiquitous that we frequently fail to appreciate its significance. While the origin of the phrase is said to be in legal contracts [cite], the necessity of time and having a common notion of time permeates all sectors, from logistics and manufacturing in industry, to the day-to-day work-life routine in private life, and even to academia, as everybody perpetually works towards the next deadline. In computer systems and communications, time has been with us from the very beginnings, with its significance showing from the most basic synchronized digital circuits even to places where one might not expect, such as in the world's most pervasive digital cryptography deployment, the SSL/TLS PKI.

Nowadays, with the availability of the internet, satellite communications and digital clocks, we often take for granted that we can tell the time anywhere and anytime. And for most use cases, a rough estimate of time on the order of magnitude of seconds is perfectly sufficient. After all, sub-second granularity is irrelevant as people follow their daily schedules, and for project plans that span years or even decades a day or two more will not make a difference. However, in communications, real-time systems and circuitry, we often operate on an entirely different scale, with sub-nanosecond-level differences quickly becoming significant in areas like chip design [cite]. Clearly, there is a very broad range of accuracies that we need to keep time in, and it is our mission to evaluate to what degree we can rely on time on modern computer systems in a range of contexts.

### Applications that require time
A classical example of an application that requires precise notions of time is geolocation. GPS and related technologies rely on signal propagation delays to determine relative positioning, and the time difference between clock sources (i.e. the satellites) needs to be precisely compensated so that delay differences can be measured accurately, thus leading to a good location estimation. Failure to compensate clock differences or even the presence of adversarial signals can quickly degrade the resulting location quality.

Timing is also critical for fault-tolerant systems. Architectures such as double- or triple-modular lock-step redundancy, where algorithms are run independently on different machines to automatically detect and correct errors, rely on a common notion of time to make progress even when a machine has failed. Such systems are found frequently in high-reliability applications such as aviation, where computer systems are relied on for controlling machinery with strict timing requirements. Failed safety-critical redundancy engineering has seen some infamous examples recently, with deadly Boeing 737-Max incidents prompting the introduction of new laws for flight control computer error resilience [cite]. Without a common notion of time, it would not be possible for resilient systems to judge internally missed deadlines correctly, thus preventing the system from providing proper error-detection and correction, voiding the fault-tolerance it was designed for.

However, time is not only critical in fault-tolerant systems, it pervades all distributed systems. High-performance and datacenter computing are areas where millions are being spent on maximizing hardware utilization by reducing idling due to I/O, and a common notion of time across systems and components is both essential to quantifying the problem and mitigating it by optimizing synchronization. The better the time source, the easier it becomes to perform efficient handovers by reducing the chance of early or late arrival, thus improving overall performance and resource savings.

Clearly, having some sort of clock synchronization is essential in almost all aspects of computing, and the range of accuracies required can be rather large. This makes it necessary to examine what our systems are capable of and what sort of reliability guarantees they can provide for our algorithms to work with.

### Methodology considerations
#### The Problem: Idempotence
There are two key aspects to timing systems that we are investigating: the final clock synchronization quality as well as the convergence to it. Time-synchronization is not idempotent, especially the convergence depends a lot on the outset conditions -- a clock that is already somewhat well synchronized is going to produce a much different profile than one that is far away from the point of convergence.

Consider the following two profiles: In the first, the clock is already synchronized with sub-millisecond precision. It only takes around 30 seconds for the clock to converge to its best precision.

![quick_convergence.png](res%2Fquick_convergence.png)
_Clock convergence is fast if the clock is already well synchronized from the start. Within just 30 seconds, our median deviation is below 10 microseconds._

On the other hand, if the clock synchronization is not optimal, then the time to convergence can be a lot longer. Here is the same benchmark when the clocks are just 0.1 seconds apart from each other to begin with:

![slow_convergence.png](res%2Fslow_convergence.png)
_Clock convergence is a lot slower in the worst case. Despite an initial offset of just a few milliseconds, the clock does not fully converge in 5 minutes._

Repeating the same benchmark several times can therefore have an undesired outcome if the starting conditions are not controlled, negatively affecting the quality of the results. The following data is from 4 identical runs of the above experiment, showing completely different observation density functions. 

![unreproducible_measurements.png](res%2Funreproducible_measurements.png)
_Rerunning the same experiment can yield wildly different results when the environment is not properly controlled._

We can remedy this by splitting the data into two phases, the converging phase and the stable phase. From the stable phase, we can extract the relevant quality metrics, while we can analyze clock trajectories from the convergence phase. However, to be able to split the data into phases we need to reliably determine what constitutes a synchronized clock.

#### Determining synchronizedness

### Hardware Setup

We are conducting the performance measurements on a Raspberry Pi 4 cluster interconnected via Ethernet.

![pi_setup_small.jpg](res%2Fpi_setup_small.jpg)

We want to be able to physically verify clock differences according to pulses sent to a microcontroller:

![hardware_setup.drawio.svg](res%2Fhardware_setup.drawio.svg)

The microcontroller reads pulses sent from each of the Raspberry-Pis and uses its internal cycle counter to determine the difference between the signals, which is later converted to an estimate of the total clock difference. Note that there are multiple sources of error that need to be estimated: The variance with which the Raspberry-Pis can emit pulses and the potential variance with which they can be read by the microcontroller. 

![pi_wiring.jpg](res%2Fpi_wiring.jpg)

#### Problem: Outputting the time signal

As stated above, the accuracy of our hardware clock evaluation depends on the Raspberry Pis being able to output reliable clock signals. Raspberry-Pis support emitting hardware clocks on GPIO pins (this is referred to as hardware PWM), which allows us to very precisely measure the Raspberry Pi's physical clock on the Arduino. When setup like this, a single Raspberry Pi's signal flanks appear almost perfectly evenly spaced to the Arduino, meaning that deviations are well below 1 microsecond. By calculating the phase difference between the two signals each emitted by a Raspberry Pi, we can thus very accurately determine the offset between the hardware clocks on both devices, and additionally determine the drift between the oscillators by tracking the phase shift over time.

However, there is one key caveat to this approach: the timing functions used by PTP (both via stepping the clock or adjusting the clock's tick-rate) never physically modify the hardware oscillator. While this might seem obvious for clock steps that modify the clock instantaneously, where it would be necessary to stop or super-charge the clock with all the unwanted hardware side-effects, this also applies to the clock slew, where clock frequency adjustments are made to gradually bring clocks closer together. Both the clock step and the clock slew modify only the kernel's internal software clock, which tracks the hardware oscillator with an offset and a rate adjustment. Thus, any adjustments to the kernel's software clock are invisible to the hardware oscillator, meaning that we cannot measure it using pure hardware support.

On the other hand, we can use software that reads the kernel's software clock and outputs a pulse at the precise boundary between two seconds (software PWM). This clock signal follows both the clock steps and any clock slew initiated by PTP, thus allowing us to measure the actual difference between the clocks. However, this approach suffers from the usual issues regarding real-time computing on commodity hardware: it is difficult to force the latency below the microsecond range due to the presence of interference by interrupts, scheduling and other system management happening in the background. This means that the signal edges occur much less precisely, negatively affecting the signal quality. A sample trace of clock differences shows this quite clearly:

![software_pwm_clock_drift.svg](res%2Fsoftware_pwm_clock_drift.svg)<br>
_Clock Drift when Emitted by Software PWM: A signal is visible but the range is over 100us._

While we can see an estimated clock drift of about 350us, the noise in the signal causes a range of over 100us, making this clock source less suitable for precision measurement. Real-time systems employ tricks like tuning the scheduler or disabling interrupts to reduce the scheduling variability. However, by doing so, we would be influencing the effect we are trying to observe in the first place, as both NTP/PTP and the kernel's timing features require interrupts to function to be able to perform their work.

The following figure illustrates the dilemma: Either we use the hardware capabilities to read the on-board oscillator causing use to inadvertently bypass NTP/PTP, or we use software to read the system clock at the cost of much worse signal quality. 

![raspberry_pi_clock_output.drawio.svg](res%2Fraspberry_pi_clock_output.drawio.svg)

This issue has yet to be resolved.

### Timekeeping on a global scale

Default-time synchronization via NTP -- with local-ish servers and servers on the other side of the world.

### Timekeeping on a local scale

PTP and accuracy over a local network.

### Detrimental conditions and Scalability

### Congestion and contention

Intuition suggests that congestion and resource contention degrade PTP's ability to synchronize clocks precisely. However, the magnitude of degradation as well as how much of it can be mitigated by careful configuration is less obvious. We therefore investigate the two shared resources that we deem affect PTP the most: access to the CPU and access to the network.

Naively, a user might install PTP and just let it run on their system using the default configuration. In this case, access to the shared resource is prioritized by the OS, which does not account for the time-criticality of PTP unless specifically configured to do so. Thus, PTP contends with all other processes trying to access the shared resource, and in the worst case the demand for the shared resource is at capacity, causing additional latency. 

For both the CPU and the network interface resources, we examine our baseline (where close to no contention for the resource occurs) in comparison to the behavior when the resource is fully loaded. Artificial load is generated by Stress-NG for the CPU and by iPerf for the network.

![load_network_unisolated_versus_linuxptp.png](res%2Fload_network_unisolated_versus_linuxptp.png)
_Sample comparison of measured clock offsets on LinuxPTP for the baseline (left) and a fully loaded network interface (right). The median clock offset is more than four times larger when contending traffic is present._

Besides the four times increase in magnitude of the clock offset, the uncertainty in the signal represented by the clock offset standard deviation increases by an order of magnitude. 

![load_network_unisolated_versus_ptpd.png](res%2Fload_network_unisolated_versus_ptpd.png)
_Similar picture for PTPd: while the median clock deviation is also around four times the baseline, key other metrics like the standard deviation, the 99th-percentile, and the path delay are completely different._

However, problems start arising when we test a range of different loads. From the following graphic, we can observe that the behavior is not stable at all:

![load_network_unisolated.png](res%2Fload_network_unisolated.png)
_Clock synchronization trend for different loading levels of the network (top) and the accompanying measured path delay (bottom). Surprisingly, additional network load can improve performance if it is light. For higher network loads, the signal starts becoming very noisy._

The first surprising finding is that performance can be increased by increasing system load. This is seen in the figure above where the clock offset is actually lower for 1% additional load than the baseline in the case of LinuxPTP. This effect can be viewed more closely in a direct comparison:

![load_base_vs_1_percent_linuxptp.png](res%2Fload_base_vs_1_percent_linuxptp.png)
_LinuxPTP clock synchronization appears to be more accurate when some amount of network load is present._

However, the same does not appear to be true for PTPd:

![load_base_vs_1_percent_ptpd.png](res%2Fload_base_vs_1_percent_ptpd.png)
_PTPd has more difficulty coping with even a small amount of load._


The general trend looks like this:


![load_network_unisolated.png](..%2F..%2Fdata%2Fcharts%2Fload%2Fload_network_unisolated.png)

The discrepancy between 80% load and 90% load for LinuxPTP:
#### 80% Load
![net_unprioritized_load_80-2024-02-07-06-27-51-LinuxPTP-processed-rpi08-series.png](..%2F..%2Fdata%2Fprofiles%2Fload%2Fnet%2Funprioritized%2Fnet_unprioritized_load_80-2024-02-07-06-27-51-LinuxPTP-processed-rpi08-series.png)

#### 90% Load
![net_unprioritized_load_90-2024-02-07-08-28-02-LinuxPTP-processed-rpi08-series.png](..%2F..%2Fdata%2Fprofiles%2Fload%2Fnet%2Funprioritized%2Fnet_unprioritized_load_90-2024-02-07-08-28-02-LinuxPTP-processed-rpi08-series.png)

The big difference is the path delay, the same comparison again:

### 80% Load

![net_unprioritized_load_80-2024-02-07-06-27-51-LinuxPTP-processed-rpi08-series-path-delay.png](..%2F..%2Fdata%2Fprofiles%2Fload%2Fnet%2Funprioritized%2Fnet_unprioritized_load_80-2024-02-07-06-27-51-LinuxPTP-processed-rpi08-series-path-delay.png)

### 90% Load
![net_unprioritized_load_90-2024-02-07-07-27-56-PTPd-processed-rpi08-series-path-delay.png](..%2F..%2Fdata%2Fprofiles%2Fload%2Fnet%2Funprioritized%2Fnet_unprioritized_load_90-2024-02-07-07-27-56-PTPd-processed-rpi08-series-path-delay.png)

### Fault Tolerance

To test fault tolerance, we first have to extend to two clients, e.g. LinuxPTP:

![1_to_2_clients_versus_base_linuxptp.png](..%2F..%2Fdata%2Fcharts%2F1_to_2%2F1_to_2_clients_versus_base_linuxptp.png)

While the effective synchronization is roughly identical, there is a noticeably higher path delay for the second client. The same effect is visible for PTPd:

![1_to_2_clients_versus_base_ptpd.png](..%2F..%2Fdata%2Fcharts%2F1_to_2%2F1_to_2_clients_versus_base_ptpd.png)

#### Software Fault

Second client stuck in a boot-loop, "crashing" every 30 seconds.

LinuxPTP:
![software_fault_clients_comparison_linuxptp.png](..%2F..%2Fdata%2Fcharts%2F1_to_2%2Fsoftware_fault_clients_comparison_linuxptp.png)
![software_fault_clients_versus_linuxptp.png](..%2F..%2Fdata%2Fcharts%2F1_to_2%2Fsoftware_fault_clients_versus_linuxptp.png)

### Hardware Fault

The network switch fails approximately every 30 seconds for 5 seconds.
![hardware_fault_clients_comparison_linuxptp.png](..%2F..%2Fdata%2Fcharts%2F1_to_2%2Fhardware_fault_clients_comparison_linuxptp.png)

### Scalability


### Measurements TODO
Measurements: Optimal polling frequency?
Which parameters generally affect the clock synchronization precision.
--> Ethernet switch: Are there switches that support priorities?
--> Try this: Perhaps using a virtual interface for priorities?
--> Do we need to establish a different baseline?
LAN Controlled Power Switch

### Requirements for a Switch/PDU
Switch: PTP Peer 2 Peer, Network Priorities
PDU: Triggered by LAN
