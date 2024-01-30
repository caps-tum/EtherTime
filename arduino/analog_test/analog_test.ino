#include <RTCZero.h>

const uint32_t CYCLES_PER_SECOND = 48 * 1000 * 1000; // 48 MHz
#define READ_PIN 6
#define READ_PIN_2 7

void setup() {

  Serial.begin(9600);

  // put your setup code here, to run once:
  pinMode(READ_PIN, INPUT_PULLUP);
  pinMode(READ_PIN_2, INPUT_PULLUP);


  pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
  // put your main code here, to run repeatedly:

  for(int i = 0; i < 10; i++) {
    digitalWrite(LED_BUILTIN, LOW);
    delay(100);
    digitalWrite(LED_BUILTIN, HIGH);
    delay(100);
  }

//  digitalWrite(LED_BUILTIN, HIGH);

  Serial.print("Begin cycle benchmark. ");

  uint32_t counter = 0;
  for(; counter < 1000;) {
    counter++;

    // #ifdef DIGITAL
    uint16_t value = digitalRead(READ_PIN);
    uint16_t value_2 = digitalRead(READ_PIN_2);
    // #else
    // uint16_t value = analogRead(READ_PIN);
    // uint16_t value_2 = analogRead(READ_PIN_2);
    // #endif
    uint16_t sum = value + value_2;
    uint16_t writeValue = (value == value_2)? HIGH : LOW;

    digitalWrite(LED_BUILTIN, writeValue);


    Serial.print(value);
    Serial.print(":");
    Serial.print(value_2);
    Serial.print(" ");
    if(counter % 30 == 0) {
      Serial.println();
    }
    delay(100);
  }

  Serial.print("Finished: ");
  Serial.print(0);
  Serial.print(" seconds = ");
  Serial.print(counter);
  Serial.print(" cycles.\n");

}
