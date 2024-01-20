# Related Work

The following lists related works on clock-synchronization and PTP.

### Performance Analysis

**Clock Synchronization Algorithms Over PTP-Unaware Networks: Reproducible Comparison Using an FPGA Testbed**
https://ieeexplore.ieee.org/abstract/document/9334990

_Useful for: Testbed-setup, algorithmic and mathematical background, analysis with and without background traffic, network hops, potential packet delays._

This work explores clock synchronization algorithms used to process timestamps from the IEEE 1588 precision time protocol (PTP). It focuses on the PTP-unaware network scenario, where the network nodes do not actively contribute to PTP's operation. This scenario typically imposes a harsh environment for accurate clock distribution, primarily due to the packet delay variation experienced by PTP packets. In this context, it is essential to process the noisy PTP measurements using algorithms and strategies that consider the underlying clock and packet delay models. This work surveys some attractive algorithms and introduces an open-source analysis library that combines several of them for better performance. It also provides an unprecedented comparison of the algorithms based on datasets acquired from a sophisticated testbed composed of field-programmable gate arrays (FPGAs). The investigation provides insights regarding the synchronization performance under various scenarios of background traffic and oscillator stability.

**Understanding and applying precision time protocol**
https://ieeexplore.ieee.org/abstract/document/7449285

_Useful for: Rough algorithm comparisons, different experiment setups, some algorithmic background_

Precise time synchronization has become a critical component of modern power systems. There are several available methods for synchronizing the intelligent electronic devices (IEDs) in a power system. In recent years, there has been great interest in providing time to the IEDs using the same infrastructure through which the data are communicated. Precision Time Protocol (PTP) is a promising technology for achieving submicrosecond synchronization accuracy between IEDs over Ethernet. This paper presents the protocol fundamentals and discusses considerations for designing power system networks to achieve submicrosecond accuracies. Specific provisions made in the profile for power system applications to support IEC 61850 substation automation systems are also discussed.

### Algorithms

**Towards a quantization based accuracy and precision characterization of packet-based time synchronization**
https://ieeexplore.ieee.org/abstract/document/7579512?casa_token=hOftKQA8-w4AAAAA:ITWTkOf5pplU9JFfCuuMDK0sw4ar7Yz7MfPkRJ-OL1S65fvds6vbsE-KoDUWqQT_-fqVtTmqUg

_Useful for: Approach to comparing clock difference signals, potential visualizations, predicting whether clock is synchronized._

Packed-based precision time synchronization is a fundamental enabling technology of modern distributed measurement and control systems. Today IEEE 1588 and derivative solutions such as IEEE 802.1AS can be considered stable technologies with wide scale support from manufacturers, and new technologies built upon them also, such as dependable, real-time communication over Ethernet (Time Sensitive Networking, TSN). However, properties of such solutions in their synchronized state; when error signals tend to be small and close to the minimum value for their numerical representation, is not well-understood, especially in complex systems configurations using several transparent clocks connecting the master clock to slave clocks. In the paper a quantization and sampling based initial approach is introduced for such packet-based time synchronization systems taking into account implementation specific details, primarily the used timestamping approach and effects of finite word-length arithmetic units used in computer systems. Based on the model some preliminary analyses results are also shown that verify that this model is applicable.


**Clock Skew Estimation Using Kalman Filter and IEEE 1588v2 PTP for Telecom Networks**
https://ieeexplore.ieee.org/abstract/document/7096944

_Useful for: theory of clock synchronization, mathematical background, overview of pre-existing algorithms._

Accurate and precise frequency synchronization is an essential requirement for different areas in telecommunication industry. Emerging practise for frequency synchronization is to utilize packet networks since it is highly cost effective. One method of distributing frequency over a variety of packet networks is based on well known IEEE 1588v2 PTP standard that uses a master-slave architecture. Accuracy and precision of the frequency synchronization over IEEE 1588v2 PTP is mainly deteriorated by the Packet Delay Variations (PDVs) experienced on the transmission path. This problem can be overcome by deploying so-called timing aware routing elements, however slaves' frequency accuracy and precision still heavily relies on the quality of the slave's clock synchronization algorithm. Hence, this work introduces an improved Kalman filter based algorithm for frequency synchronization over IEEE 1588v2 protocol that outperforms other prior art techniques. The algorithm's performance is evaluated using simulation, yet the network impairments (PDVs) are based on experimentally measured data.

**Characterizing grandmaster, transparent, and boundary clocks with a precision packet probe and packet metrics**
https://ieeexplore.ieee.org/document/6070160

_Useful for: Clock comparison methodology, characterization of clock divergence_

The IEEE 1588 packet probe has proved to be an effective tool for the measurement and analysis of network packet delay variation and latency. As more and more IEEE 1588 equipment is designed and deployed in the service of telecommunications networks and for other applications, in some cases with on-path support provided by boundary or transparent clocks, it has become important to be able to characterize this equipment. In many cases the packets themselves are the only timing signal available for study. Thus the packet probe is an essential tool for characterizing this equipment. Likewise, the same metrics developed for the analysis of network packet delay variation can be employed for equipment characterization. This paper, drawing on measurements of commercial equipment, describes how a packet probe along with traditional stability metrics and recently developed packet metrics can be used to characterize IEEE 1588 grandmaster clocks, boundary clocks, and transparent clocks.

**On the Accuracy and Stablility of Clocks Synchronized by the Network Time Protocol in the Internet System**
https://dl.acm.org/doi/abs/10.1145/86587.86591

_Useful for: Large-scale (global) evaluation of synchronization accuracy for NTP._

This paper describes a series of experiments involving over 100,000 hosts of the Internet system and located in the U.S., Europe and the Pacific. The experiments are designed to evaluate the availability, accuracy and reliability of international standard time distribution using the Internet and the Network Time Protocol (NTP), which has been designated an Internet Standard protocol. NTP is designed specifically for use in a large, diverse internet system operating at speeds from mundane to lightwave. In NTP a distributed subnet of time servers operating in a self-organizing, hierarchical, master-slave configuration exchange precision timestamps in order to synchronize host clocks to each other and national time standards via wire or radio.The experiments are designed to locate Internet hosts and gateways that provide time by one of three time distribution protocols and evaluate the accuracy of their indications. For those hosts that support NTP, the experiments determine the distribution of errors and other statistics over paths spanning major portions of the globe. Finally, the experiments evaluate the accuracy and reliability of precision timekeeping using NTP and typical Internet paths involving ARPANET, NSFNET and regional networks. The experiments demonstrate that timekeeping throughout most portions of the Internet can be maintained to an accuracy of a few tens of milliseconds and a stability of a few milliseconds per day, even in cases of failure or disruption of clocks, time servers or networks.

**Highly Accurate Timestamping for Ethernet-Based Clock Synchronization**
https://www.hindawi.com/journals/jcnc/2012/152071/

_Useful for: Beyond hardware support, claimed sub-nanosecond synchronization accuracy_

It is not only for test and measurement of great importance to synchronize clocks of networked devices to timely coordinate data acquisition. In this context the seek for high accuracy in Ethernet-based clock synchronization has been significantly supported by enhancements to the Network Time Protocol (NTP) and the introduction of the Precision Time Protocol (PTP). The latter was even applied to instrumentation and measurement applications through the introduction of LXI. These protocols are usually implemented in software; however, the synchronization accuracy can only substantially be improved by hardware which supports drawing of precise event timestamps. Especially, the quality of the timestamps for ingress and egress synchronization packets has a major influence on the achievable performance of a distributed measurement or control system. This paper analyzes the influence of jitter sources remaining despite hardware support and proposes enhanced methods for up to now unmatched timestamping accuracy in Ethernet-based synchronization protocols. The methods shown in this paper reach sub-nanosecond accuracy, which is proven in theory and practice.



### Hardware

**Hardware Assisted Clock Synchronization with the IEEE 1588-2008 Precision Time Protocol**
https://dl.acm.org/doi/abs/10.1145/3273905.3273920

_Useful for: Implementation of PTP on FPGA, Hardware-accelerated synchronization experimental analysis._

Emerging technologies such as Fog Computing and Industrial Internet-of-Things have identified the IEEE 802.1Q amendment for Time-Sensitive Networking (TSN) as the standard for time-predictable networking. TSN is based on the IEEE 1588-2008 Precision Time Protocol (PTP) to provide a global notion of time over the local area network. Commonly, off-the-shelf systems implement the PTP in software where it has been shown to achieve microsecond accuracy. In the context of Fog Computing, it is hypothesized that future industrial systems will be equipped with FPGAs. Leveraging their inherent flexibility, the required PTP mechanisms can be implemented with minimal hardware usage and can achieve comparable synchronization results without the need for a PTP-capable transceiver. This paper investigates the practical challenges of implementing the PTP and proposes a hardware architecture that combines hardware-based timestamping with a rate adjustable clock design. The proposed architecture is integrated with the Patmos processor and evaluated on an experimental setup composed of two FPGA boards communicating through a commercial-off-the-shelf switch. The proposed implementation achieves sub-microsecond clock synchronization with a worst-case offset of 138 ns.


### Applications of PTP

**A Combined PTP and Circuit-Emulation System**
https://ieeexplore.ieee.org/abstract/document/4383789

_Useful for: Sample application of PTP (traditional time-multiplexed telecommunications via packet-switched networks)_

This paper describes a telecom circuit-emulation system that uses the precision time protocol (PTP) aka IEEE1588 for frequency distribution. The advantages of the use of PTP compared with traditional clock recovery mechanism are discussed. The architecture and its main design consideration are reviewed and preliminary performance tests results are demonstrated.

**Clock synchronization of PTP-based devices through PROFINET IO networks** 
https://ieeexplore.ieee.org/abstract/document/4638445

_Useful for: Application of PTP in embedded networks (PROFINET)_

The paper deals with IEEE1588 PTP-based devices which are installed in industrial plants together with PROFINET IO Class C. In fact, devices with PTP for clock synchronization (e.g. LXI instruments, Ethernet/IP nodes etc.) exhibit noticeable time errors if directly connected to the PROFINET infrastructure. In the paper, possible architectures to overcome this limitation are evaluated (i.e boundary clock), then an intelligent clock synchronization converter is proposed. The core idea is to create a black-box that does not require configuration neither of the PTP-based nodes nor of the host plant. The proposed converter has been applied to a PROFINET IO network that hosts PTP-based devices. Preliminary results show that, if compared with a direct connection of PTP-based nodes, the converter worsens the synchronization accuracy of less than 10 ns.

### Miscellaneous Notes

Allan Variance: Measure of clock frequency stability (https://en.wikipedia.org/wiki/Allan_variance)
