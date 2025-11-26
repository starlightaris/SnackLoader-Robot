#include <WiFi.h>

const char* ssid = "Your_WIFI";
const char* password = "Your_Password";

void setup() {
  Serial.begin(115200);
  
  Serial.print("Connecting to WiFi...");
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }

  Serial.println("\nConnected!");
  Serial.println(WiFi.localIP());
}

void loop() {}
