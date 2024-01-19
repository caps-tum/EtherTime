
# Spend some Time on Time / It is Time to Talk about Time
_Vincent Bode, Arpan Gujarati_

### Motivation

"Time is of the essence", to many readers this might only be an idiom but the relevance of time is so ubiquitous that we frequently fail to appreciate its significance. While the origins of the phrase are said to be in legal contracts [cite], the necessity of time and having a common notion of it permeates all sectors, from logistics and manufacturing over sports and leisure even to academia, as we all perpetually flow towards the next deadline. In computer systems and communications, time has been with us from the very beginnings, with its significance showing even in places where one might not expect, such as in the world's most pervasive digital cryptography deployment, the SSL/TLS PKI.

Nowadays, with the availability of the internet, satellite communications and digital clocks, we often take for granted that we can tell the time anywhere and anytime. And for most use cases, a rough estimate of time on the order of magnitude of seconds is perfectly sufficient. _After all, it does not really matter how many seconds late your grandparents show up for dinner, and for project plans that span years or even decades a day or two more will not make a difference._ However, in communications, real-time systems and circuitry, we often operate on an entirely different scale, with sub-nanosecond-level differences quickly becoming significant in areas like chip design [cite]. Clearly, there is a very broad range of accuracies that we need to keep time in, and it is our mission to evaluate to what degree we can rely on time on modern computer systems in a range of contexts.

### Applications that require time
Fault-Tolerance systems, with the possibility of affecting safety/security.

Performance measurements, especially distributed ones.

### Methodology considerations
#### The Problem: Idempotence
There are two key aspects to timing systems that we are investigating: the final clock synchronization quality as well as the convergence to it. Time-synchronization is not idempotent, especially the convergence depends a lot on the outset conditions -- a clock that is already somewhat well synchronized is going to produce a much different profile than one that is far away from the point of convergence.

Consider the following two profiles: In the first, the clock is already synchronized with sub-millisecond precision. It only takes around 30 seconds for the clock to converge to its best precision.

![quick_convergence.png](res%2Fquick_convergence.png)
_Clock convergence is fast if the clock is already well synchronized from the start. Within just 30 seconds, our median deviation is below 10 microseconds._

On the other hand, if the clock synchronization is not optimal, then the time to convergence can be a lot longer. Here is the same benchmark when the clocks are just 0.1 seconds apart from each other to begin with:

![slow_convergence.png](res%2Fslow_convergence.png)
_Clock convergence is a lot slower in the worst case. Despite an initial offset of just a few milliseconds, the clock does not fully converge in 5 minutes._

Repeating the same benchmark several times can therefore have an undesired outcome if the starting conditions are not controlled, negatively affecting the quality of the results.

![unreproducible_measurements.png](res%2Funreproducible_measurements.png)
_Rerunning the same experiment can yield wildly different results when the environment is not properly controlled._

We can remedy this by splitting the data into two phases, the converging phase and the stable phase. From the stable phase, we can extract the relevant quality metrics, while we can analyze clock trajectories from the convergence phase. However, to be able to split the data into phases we need to reliably determine what constitutes a synchronized clock.

#### Determining synchronizedness

### Hardware Setup

We are conducting the performance measurements on a Raspberry Pi 4 cluster interconnected via Ethernet.

![pi_setup_small.jpg](res%2Fpi_setup_small.jpg)

We want to be able to physically verify clock differences according to pulses sent to a microcontroller:

![setup_schematic.png](res%2Fsetup_schematic.png)

### Timekeeping on a global scale

Default-time synchronization via NTP -- with local-ish servers and servers on the other side of the world.

### Timekeeping on a local scale

PTP and accuracy over a local network.

### Detrimental conditions and Scalability

Congestion and contention

Many nodes

