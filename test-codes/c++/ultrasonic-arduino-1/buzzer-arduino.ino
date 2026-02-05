#define LED 2
#define BUZZER 13

void setup() {
  pinMode(LED, OUTPUT);
  pinMode(BUZZER, OUTPUT);
}

void loop() {
  digitalWrite(LED, HIGH);
  tone(BUZZER, 1000);
  delay(500);

  digitalWrite(LED, LOW);
  noTone(BUZZER);
  delay(500);
}
