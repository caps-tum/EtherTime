
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

![setup_schematic.png](res%2Fsetup_schematic.png)

The microcontroller reads pulses sent from each of the Raspberry-Pis and uses its internal cycle counter to determine the difference between the signals, which is later converted to an estimate of the total clock difference. Note that there are multiple sources of error that need to be estimated: The variance with which the Raspberry-Pis can emit pulses and the potential variance with which they can be read by the microcontroller. 

### Timekeeping on a global scale

Default-time synchronization via NTP -- with local-ish servers and servers on the other side of the world.

### Timekeeping on a local scale

PTP and accuracy over a local network.

### Detrimental conditions and Scalability

Congestion and contention

Many nodes

