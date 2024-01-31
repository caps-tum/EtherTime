#include <Arduino.h>
#include <RTCZero.h>

const uint32_t CYCLES_PER_SECOND = 48 * 1000 * 1000; // 48 MHz

const size_t NUM_TRACES = 1;

// Must be a power of 2
const size_t TRACE_LENGTH = 1024;

typedef struct {
  uint8_t pin = 0;
  size_t index = 0;
  uint32_t timestamps[TRACE_LENGTH];
  uint32_t state[TRACE_LENGTH];
} trace_t;

trace_t trace;

// Calculate the bit mask of register bits we need
#define PIN_1 6
#define PIN_2 7
// const uint32_t GPIO_READ_BITMASK = (1ul << g_APinDescription[PIN_1].ulPin)) | (1ul << g_APinDescription[PIN_2].ulPin))
const PortGroup* READ_PORT = digitalPinToPort(PIN_1);
const PortGroup* READ_PORT_2 = digitalPinToPort(PIN_1);
// _Static_assert(READ_PORT == READ_PORT_2, "Read pin 1 needs to be on the same port as read pin 2");
const volatile void* READ_REGISTER = portInputRegister(READ_PORT);

#define READ_MASK_PIN_1 digitalPinToBitMask(PIN_1)
#define READ_MASK_PIN_2 digitalPinToBitMask(PIN_2)
const uint32_t READ_MASK = READ_MASK_PIN_1 | READ_MASK_PIN_2;
#define READ_ALL_PINS (*((uint32_t*)READ_REGISTER) & READ_MASK)

RTCZero rtc;

void setup() {

  Serial.begin(9600);
  rtc.begin();


  pinMode(PIN_1, INPUT_PULLUP);
  pinMode(PIN_2, INPUT_PULLUP);

  // put your setup code here, to run once:
  pinMode(LED_BUILTIN, OUTPUT);
}

void printTrace(unsigned int traceNumber, uint32_t bitmask) {
  Serial.print("Trace ");
  Serial.println(traceNumber);

  for(size_t index = 1; index < trace.index; index++) {
    // Check if the bit in question changed (important: start at index 1 to prevent underflow).
    if((trace.state[index - 1] & bitmask)
       != (trace.state[index] & bitmask)) {
      Serial.print(trace.timestamps[index]);
      Serial.print(" ");
    }
  }
  Serial.println("");
}

void loop() {
  // put your main code here, to run repeatedly:

  for(int i = 0; i < 30; i++) {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(100);
    digitalWrite(LED_BUILTIN, LOW);
    delay(100);
  }

//  rtc.setDate(1970, 1, 1);
  rtc.setTime(0, 0, 0);

  Serial.println("Begin cycle benchmark.");
  Serial.flush();


  trace.index = 0;
  trace.state[trace.index] = READ_ALL_PINS;

  noInterrupts();
  uint32_t cycles = 0;
  uint32_t start = micros();
  // for(; cycles < 1 * 1000000;) {
  //   cycles++;
  // uint32_t flanksRecorded = 0;
  while(trace.index < TRACE_LENGTH - 1) {

    // Read the pins, all at once using a register.
    // bool result = digitalRead(traces[trace].pin);
    uint32_t result = READ_ALL_PINS;

    if(result != trace.state[trace.index]) {
      // And the index with the trace length - 1, preventing the index from exceeding buffer size.
      trace.index = (trace.index + 1) & (TRACE_LENGTH - 1);

      // Methods to read the time: number of loop cycles, using a register, or the arduino function
      // traces[trace].data[index] = cycles;
      trace.timestamps[trace.index] = SysTick->VAL;
      // traces[trace].data[index] = micros();

      trace.state[trace.index] = result;
      //digitalWrite(LED_BUILTIN, result);

      // flanksRecorded++;
      // if(flanksRecorded >= TRACE_LENGTH - 1) {
      //   break;
      // }
    }
    // delay(1);
    //delayMicroseconds(1);
  }
  interrupts();

  uint32_t stop = micros();
  uint32_t final_time = rtc.getSeconds();

  Serial.print("Finished: ");
  Serial.print(final_time);
  Serial.print(" seconds = ");
  Serial.print(stop - start);
  Serial.print(" us, cycles = ");
  Serial.print(cycles);
  Serial.print("\n");
  Serial.flush();

  printTrace(0, READ_MASK_PIN_1);
  printTrace(1, READ_MASK_PIN_2);

}
