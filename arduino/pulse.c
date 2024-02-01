// Using code from here: https://github.com/hzeller/rpi-gpio-dma-demo/blob/master/gpio-dma-test.c#L39

#include <assert.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include <stdbool.h>
#include <time.h>
#include <sched.h>


#define BCM2711_PI4_PERI_BASE  0xFE000000
#define PERI_BASE BCM2711_PI4_PERI_BASE
#define TOGGLE_GPIO 26

#define PAGE_SIZE 4096

// ---- GPIO specific defines
#define GPIO_REGISTER_BASE 0x200000
#define GPIO_SET_OFFSET 0x1C
#define GPIO_CLR_OFFSET 0x28
#define PHYSICAL_GPIO_BUS (0x7E000000 + GPIO_REGISTER_BASE)


// Return a pointer to a periphery subsystem register.
static void *mmap_bcm_register(off_t register_offset) {
  const off_t base = PERI_BASE;

  int mem_fd;
  if ((mem_fd = open("/dev/mem", O_RDWR|O_SYNC) ) < 0) {
    perror("can't open /dev/mem: ");
    fprintf(stderr, "You need to run this as root!\n");
    return NULL;
  }

  uint32_t *result =
    (uint32_t*) mmap(NULL,                  // Any address in our space will do
                     PAGE_SIZE,
                     PROT_READ|PROT_WRITE,  // Enable r/w on GPIO registers.
                     MAP_SHARED,
                     mem_fd,                // File to map
                     base + register_offset // Offset to bcm register
                     );
  close(mem_fd);

  if (result == MAP_FAILED) {
    fprintf(stderr, "mmap error %p\n", result);
    return NULL;
  }
  return result;
}

void initialize_gpio_for_output(volatile uint32_t *gpio_registerset, int bit) {
  *(gpio_registerset+(bit/10)) &= ~(7<<((bit%10)*3));  // prepare: set as input
  *(gpio_registerset+(bit/10)) |=  (1<<((bit%10)*3));  // set as output.
}

void run_cpu_direct() {
  // Prepare GPIO
  volatile uint32_t *gpio_port = mmap_bcm_register(GPIO_REGISTER_BASE);
  initialize_gpio_for_output(gpio_port, TOGGLE_GPIO);
  volatile uint32_t *set_reg = gpio_port + (GPIO_SET_OFFSET / sizeof(uint32_t));
  volatile uint32_t *clr_reg = gpio_port + (GPIO_CLR_OFFSET / sizeof(uint32_t));

  struct timespec current_time = {
    .tv_sec = 0,
    .tv_nsec = 0,
  };
  long last_nsec = 0;

  // Set scheduler to realtime
  struct sched_param schedparm;
  memset(&schedparm, 0, sizeof(schedparm));
  schedparm.sched_priority = 99; // highest rt priority
  sched_setscheduler(0, SCHED_FIFO, &schedparm);

  // Do it. Endless loop, directly setting.
  printf("Starting pulses 1 per second.\n");
  for (;;) {
    usleep(900 * 1000);
    // Wait for nsec counter to flow backwards;
    do {
        last_nsec = current_time.tv_nsec;
        if(clock_gettime(CLOCK_REALTIME, &current_time)) {
            abort();
        }
    } while(last_nsec <= current_time.tv_nsec);

    *set_reg = (1<<TOGGLE_GPIO);

    last_nsec = current_time.tv_nsec;
    clock_gettime(CLOCK_REALTIME, &current_time);
    printf("Signal: %lu - %lu ns\n", last_nsec, current_time.tv_nsec);

    usleep(900 * 1000);
    // Wait for nsec counter to flow backwards;
    do {
        last_nsec = current_time.tv_nsec;
        if(clock_gettime(CLOCK_REALTIME, &current_time)) {
            abort();
        }
    } while(last_nsec <= current_time.tv_nsec);

    *clr_reg = (1<<TOGGLE_GPIO);

    last_nsec = current_time.tv_nsec;
    clock_gettime(CLOCK_REALTIME, &current_time);
    printf("Signal: %lu - %lu ns\n", last_nsec, current_time.tv_nsec);
  }
}

int main(int argc, char** argv) {
    (void)argc; (void)argv;
    run_cpu_direct();
}