#include <EEPROM.h>

void setup() {
  Serial.begin(115200);
  EEPROM.begin(512);

  EEPROM.write(0, 55);
  EEPROM.commit();

  Serial.print("Stored value: ");
  Serial.println(EEPROM.read(0));
}

void loop() {}
