#define PUMP_PIN 16

void setup() {
  Serial.begin(115120);
  pinMode(PUMP_PIN, OUTPUT);
  Serial.println("Pump Test Started");
}

void loop() {
  digitalWrite(PUMP_PIN, HIGH);
  Serial.println("Pump ON");
  delay(2000);

  digitalWrite(PUMP_PIN, LOW);
  Serial.println("Pump OFF");
  delay(2000);
}
