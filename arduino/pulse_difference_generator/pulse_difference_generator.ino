#include <RTCZero.h>

const uint32_t CYCLES_PER_SECOND = 48 * 1000 * 1000; // 48 MHz

const size_t NUM_TRACES = 2;
const size_t TRACE_LENGTH = 1024;
typedef struct {
  uint8_t pin = 0;
  uint8_t lastState = 0;
  size_t index = 0;
  uint32_t data[TRACE_LENGTH];
} trace_t;

trace_t traces[NUM_TRACES];


RTCZero rtc;

void setup() {

  Serial.begin(9600);
  rtc.begin();

  // Trace mappings
  traces[0].pin = 6;
  traces[1].pin = 7;

  // Initialize traces
  for(size_t i = 0; i < NUM_TRACES; i++) {
    traces[i].index = 0;
    pinMode(traces[i].pin, INPUT_PULLUP);
  }

  // put your setup code here, to run once:
  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  // put your main code here, to run repeatedly:

  for(int i = 0; i < 10; i++) {
    digitalWrite(LED_BUILTIN, HIGH);
    delay(100);
    digitalWrite(LED_BUILTIN, LOW);
    delay(100);
  }

  Serial.print("Begin cycle benchmark. ");

  // Reset traces
  for(size_t i = 0; i < NUM_TRACES; i++) {
    traces[i].index = 0;
  }

//  rtc.setDate(1970, 1, 1);
  rtc.setTime(0, 0, 0);

  uint32_t counter = 0;
  for(; counter < 10 * 1000000;) {
    counter++;

    for(size_t trace = 0; trace < NUM_TRACES; trace++) {
      bool result = digitalRead(traces[trace].pin);
      if(result != traces[trace].lastState) {
        traces[trace].lastState = result;
        digitalWrite(LED_BUILTIN, result);
        traces[trace].data[traces[trace].index] = counter;
        traces[trace].index++;
        if(traces[trace].index >= TRACE_LENGTH - 1) {
          traces[trace].index = TRACE_LENGTH - 1; 
        }
      }
      // delay(1);
      delayMicroseconds(1);
    }
    
  }

  uint32_t final_time = rtc.getSeconds();

  Serial.print("Finished: ");
  Serial.print(final_time);
  Serial.print(" seconds = ");
  Serial.print(counter);
  Serial.print(" cycles.\n");

  for(size_t trace = 0; trace < NUM_TRACES; trace++) {
    Serial.print("Trace ");
    Serial.println(trace);
    for(size_t index = 0; index < traces[trace].index; index++) {
      Serial.print(traces[trace].data[index]);
      Serial.print(" ");
    }
    Serial.println("");
  }
}
