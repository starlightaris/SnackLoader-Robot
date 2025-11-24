#include <WiFi.h>
#include <PubSubClient.h>

const char* ssid = "WifiName";
const char* password = "WifiPassword";
const char* mqtt_server = "broker.hivemq.com";

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) delay(500);
}

void callback(char* topic, byte* message, unsigned int length) {
  Serial.print("Received: ");
  for (int i = 0; i < length; i++) {
    Serial.print((char)message[i]);
  }
  Serial.println();
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    client.connect("pet_feeder_test");
  }
  client.loop();

  client.publish("pet/test", "hello");
  delay(1000);
}
