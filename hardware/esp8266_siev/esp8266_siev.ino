/*
  SIEV ESP8266 Firmware v1.2.0
  
  Firmware con soporte modular para sensores IMU y comunicación ESP-NOW
  Actualmente soporta BNO055, fácilmente intercambiable
  
  Hardware:
  - ESP8266 (cualquier variante)
  - BNO055 IMU conectado por I2C (SDA=GPIO4, SCL=GPIO5)
  - LEDs externos en GPIO12 (LEFT) y GPIO14 (RIGHT)
  - Comunicación serie: 115200 baud, 8N1
  
  Comandos disponibles:
  - PING, STATUS, VERSION, RESET
  - LED_ON:LEFT/RIGHT/BOTH, LED_OFF:LEFT/RIGHT/BOTH
  - IMU_READ_ONE, IMU_READ_LIVE_ON, IMU_READ_LIVE_OFF, IMU_CALIBRATE
  - ESPNOW_ON, ESPNOW_OFF, ESPNOW_PAIR:MAC, ESPNOW_STATUS
  - GADGET_SEND:DATA, OTA_START, OTA_STOP
  
  Autor: Sistema SIEV
  Fecha: 2025-07-03
*/

#include <Wire.h>
#include <ESP8266WiFi.h>
#include <espnow.h>
#include <ArduinoOTA.h>

// ===== CONFIGURACIÓN DE SENSOR IMU =====
#define USE_BNO055  // Cambiar aquí para usar otro sensor
// #define USE_MPU6050  // Ejemplo para futuro
// #define USE_LSM9DS1  // Ejemplo para futuro

#ifdef USE_BNO055
  #include <Adafruit_Sensor.h>
  #include <Adafruit_BNO055.h>
  #include <utility/imumaths.h>
#endif

// ===== CONFIGURACIÓN GENERAL =====
#define FIRMWARE_VERSION "1.2.0"
#define DEVICE_NAME "SIEV_ESP8266"
#define SERIAL_BAUD 115200
#define COMMAND_TIMEOUT 5000
#define MAX_COMMAND_LENGTH 32
#define LEFT_LED_PIN 12   // GPIO12
#define RIGHT_LED_PIN 14  // GPIO14

// Configuración I2C
#define SDA_PIN 4  // GPIO4 (D2 en NodeMCU)
#define SCL_PIN 5  // GPIO5 (D1 en NodeMCU)

// Configuración IMU Stream
#define IMU_SAMPLE_RATE_HZ 50
#define IMU_SAMPLE_INTERVAL_MS (1000 / IMU_SAMPLE_RATE_HZ)

// Configuración ESP-NOW
#define ESPNOW_CHANNEL 1
#define MAX_GADGETS 3
#define ESPNOW_MAX_DATA_LEN 250

// Configuración OTA
#define OTA_PASSWORD "siev2025"
#define OTA_HOSTNAME "siev-esp8266"

// ===== ESTRUCTURA DE DATOS ESP-NOW =====
typedef struct {
  uint8_t command;      // Tipo de comando
  uint8_t dataLen;      // Longitud de datos
  char data[248];       // Datos del comando
} ESPNowMessage;

typedef struct {
  uint8_t mac[6];
  bool active;
  unsigned long lastSeen;
  String name;
} GadgetInfo;

// ===== COMANDOS ESP-NOW =====
enum ESPNowCommands {
  CMD_PING = 0x01,
  CMD_DATA = 0x02,
  CMD_STATUS = 0x03,
  CMD_FORWARD_TO_PYTHON = 0x10,
  CMD_FORWARD_TO_GADGET = 0x11
};
class IMUSensor {
public:
  virtual bool init() = 0;
  virtual bool isConnected() = 0;
  virtual bool readAccel(float &x, float &y, float &z) = 0;
  virtual bool readGyro(float &x, float &y, float &z) = 0;
  virtual bool readMag(float &x, float &y, float &z) = 0;
  virtual bool readQuaternion(float &w, float &x, float &y, float &z) = 0;
  virtual float readTemperature() = 0;
  virtual String getCalibrationStatus() = 0;
  virtual String getSensorName() = 0;
};

// ===== IMPLEMENTACIÓN BNO055 =====
#ifdef USE_BNO055
class BNO055Sensor : public IMUSensor {
private:
  Adafruit_BNO055 bno;
  
public:
  BNO055Sensor() : bno(55, 0X29) {}
  
  bool init() override {
    if (!bno.begin()) {
      return false;
    }
    
    delay(1000);
    bno.setExtCrystalUse(true);
    return true;
  }
  
  bool isConnected() override {
    sensors_event_t event;
    bno.getEvent(&event);
    return !isnan(event.orientation.x);
  }
  
  bool readAccel(float &x, float &y, float &z) override {
    sensors_event_t event;
    bno.getEvent(&event, Adafruit_BNO055::VECTOR_ACCELEROMETER);
    if (isnan(event.acceleration.x)) return false;
    
    x = event.acceleration.x;
    y = event.acceleration.y;
    z = event.acceleration.z;
    return true;
  }
  
  bool readGyro(float &x, float &y, float &z) override {
    sensors_event_t event;
    bno.getEvent(&event, Adafruit_BNO055::VECTOR_GYROSCOPE);
    if (isnan(event.gyro.x)) return false;
    
    x = event.gyro.x;
    y = event.gyro.y;
    z = event.gyro.z;
    return true;
  }
  
  bool readMag(float &x, float &y, float &z) override {
    sensors_event_t event;
    bno.getEvent(&event, Adafruit_BNO055::VECTOR_MAGNETOMETER);
    if (isnan(event.magnetic.x)) return false;
    
    x = event.magnetic.x;
    y = event.magnetic.y;
    z = event.magnetic.z;
    return true;
  }
  
  bool readQuaternion(float &w, float &x, float &y, float &z) override {
    imu::Quaternion quat = bno.getQuat();
    if (isnan(quat.w())) return false;
    
    w = quat.w();
    x = quat.x();
    y = quat.y();
    z = quat.z();
    return true;
  }
  
  float readTemperature() override {
    int8_t temp = bno.getTemp();
    return (float)temp;
  }
  
  String getCalibrationStatus() override {
    uint8_t system, gyro, accel, mag = 0;
    bno.getCalibration(&system, &gyro, &accel, &mag);
    
    String status = "UNCALIBRATED";
    if (system >= 3 && gyro >= 3 && accel >= 3 && mag >= 3) {
      status = "FULLY_CALIBRATED";
    } else if (system >= 2 || gyro >= 2 || accel >= 2 || mag >= 2) {
      status = "PARTIAL";
    } else if (system >= 1 || gyro >= 1 || accel >= 1 || mag >= 1) {
      status = "GOOD";
    }
    
    return "SYS:" + String(system) + ",GYRO:" + String(gyro) + 
           ",ACC:" + String(accel) + ",MAG:" + String(mag) + ",STATUS:" + status;
  }
  
  String getSensorName() override {
    return "BNO055";
  }
};
#endif

// ===== VARIABLES GLOBALES =====
String inputBuffer = "";
unsigned long bootTime = 0;

// LEDs
bool leftLedState = false;
bool rightLedState = false;

// IMU
#ifdef USE_BNO055
BNO055Sensor* imuSensor = nullptr;
#endif

bool imuInitialized = false;
bool imuLiveMode = false;
unsigned long lastIMURead = 0;

// ESP-NOW
bool espnowEnabled = false;
bool otaEnabled = false;
GadgetInfo gadgets[MAX_GADGETS];
int gadgetCount = 0;
ESPNowMessage incomingMessage;
ESPNowMessage outgoingMessage;

// ===== SETUP =====
void setup() {
  // Inicializar comunicación serie
  Serial.begin(SERIAL_BAUD);
  while (!Serial) {
    delay(10);
  }
  
  // Configurar LEDs
  pinMode(LEFT_LED_PIN, OUTPUT);
  pinMode(RIGHT_LED_PIN, OUTPUT);
  digitalWrite(LEFT_LED_PIN, HIGH);   // HIGH = apagado
  digitalWrite(RIGHT_LED_PIN, HIGH);  // HIGH = apagado
  
  // Inicializar WiFi en modo STA (desactivado)
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  
  // Inicializar I2C
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000); // 400kHz
  
  // Inicializar IMU
  initIMU();
  
  // Inicializar ESP-NOW (desactivado por defecto)
  initESPNowStructures();
  
  // Guardar tiempo de inicio
  bootTime = millis();
  
  // Mensaje de inicio
  delay(100);
  Serial.println("SYSTEM:SIEV_ESP8266_READY_v" + String(FIRMWARE_VERSION));
  Serial.flush();
  
  // Reservar buffer
  inputBuffer.reserve(MAX_COMMAND_LENGTH);
  
  // LED de confirmación
  blinkLED(3, 200);
  
  Serial.println("DEBUG:IMU_STATUS:" + String(imuInitialized ? "OK" : "FAILED"));
  Serial.println("DEBUG:ESPNOW_STATUS:DISABLED");
  Serial.println("DEBUG:OTA_STATUS:DISABLED");
}

// ===== INICIALIZACIÓN ESP-NOW =====
void initESPNowStructures() {
  // Limpiar array de gadgets
  for (int i = 0; i < MAX_GADGETS; i++) {
    memset(gadgets[i].mac, 0, 6);
    gadgets[i].active = false;
    gadgets[i].lastSeen = 0;
    gadgets[i].name = "";
  }
  gadgetCount = 0;
}

bool startESPNow() {
  if (espnowEnabled) {
    return true; // Ya está activado
  }
  
  // Inicializar ESP-NOW
  if (esp_now_init() != 0) {
    Serial.println("ERROR:ESPNOW_INIT_FAILED");
    return false;
  }
  
  // Configurar canal
  esp_now_set_self_role(ESP_NOW_ROLE_COMBO);
  
  // Registrar callbacks
  esp_now_register_recv_cb(onESPNowDataReceived);
  esp_now_register_send_cb(onESPNowDataSent);
  
  espnowEnabled = true;
  Serial.println("DEBUG:ESPNOW_STARTED");
  return true;
}

void stopESPNow() {
  if (!espnowEnabled) {
    return;
  }
  
  esp_now_deinit();
  espnowEnabled = false;
  
  // Limpiar gadgets
  initESPNowStructures();
  
  Serial.println("DEBUG:ESPNOW_STOPPED");
}

// ===== CALLBACKS ESP-NOW =====
void onESPNowDataReceived(uint8_t *mac_addr, uint8_t *data, uint8_t data_len) {
  if (data_len < sizeof(ESPNowMessage)) {
    return;
  }
  
  memcpy(&incomingMessage, data, sizeof(ESPNowMessage));
  
  // Actualizar información del gadget
  updateGadgetInfo(mac_addr);
  
  // Procesar mensaje según comando
  switch (incomingMessage.command) {
    case CMD_PING:
      handleESPNowPing(mac_addr);
      break;
      
    case CMD_FORWARD_TO_PYTHON:
      // Reenviar al Python vía Serial
      Serial.print("GADGET_DATA:");
      Serial.print(macToString(mac_addr));
      Serial.print(":");
      Serial.println(incomingMessage.data);
      break;
      
    case CMD_DATA:
      // Datos generales del gadget
      Serial.print("GADGET_MSG:");
      Serial.print(macToString(mac_addr));
      Serial.print(":");
      Serial.println(incomingMessage.data);
      break;
  }
}

void onESPNowDataSent(uint8_t *mac_addr, uint8_t status) {
  // Opcional: reportar estado de envío
  if (status != 0) {
    Serial.println("ERROR:ESPNOW_SEND_FAILED:" + macToString(mac_addr));
  }
}
void initIMU() {
#ifdef USE_BNO055
  imuSensor = new BNO055Sensor();
  imuInitialized = imuSensor->init();
  
  if (imuInitialized) {
    Serial.println("DEBUG:BNO055_INITIALIZED");
  } else {
    Serial.println("ERROR:BNO055_INIT_FAILED");
    delete imuSensor;
    imuSensor = nullptr;
  }
#else
  Serial.println("ERROR:NO_IMU_CONFIGURED");
#endif
}

// ===== LOOP PRINCIPAL =====
void loop() {
  // Procesar comandos serie
  processSerialCommands();
  
  // Procesar stream IMU si está activo
  if (imuLiveMode && imuInitialized) {
    processIMULiveStream();
  }
  
  // Procesar OTA si está habilitado
  if (otaEnabled) {
    ArduinoOTA.handle();
  }
  
  delay(1);
}

// ===== PROCESAMIENTO DE COMANDOS =====
void processSerialCommands() {
  while (Serial.available()) {
    char receivedChar = Serial.read();
    
    if (receivedChar == '\r' || receivedChar == '\n') {
      if (inputBuffer.length() > 0) {
        processCommand(inputBuffer);
        inputBuffer = "";
      }
    }
    else if (inputBuffer.length() < MAX_COMMAND_LENGTH - 1) {
      inputBuffer += receivedChar;
    }
    else {
      inputBuffer = "";
      Serial.println("ERROR:COMMAND_TOO_LONG");
    }
  }
}

void processCommand(String command) {
  command.trim();
  command.toUpperCase();
  
  // Comandos básicos existentes
  if (command == "PING") {
    handlePingCommand();
  }
  else if (command == "STATUS") {
    handleStatusCommand();
  }
  else if (command == "VERSION") {
    handleVersionCommand();
  }
  else if (command == "RESET") {
    handleResetCommand();
  }
  else if (command.startsWith("LED_ON:")) {
    handleLedCommand(command, true);
  }
  else if (command.startsWith("LED_OFF:")) {
    handleLedCommand(command, false);
  }
  // Nuevos comandos IMU
  else if (command == "IMU_READ_ONE") {
    handleIMUReadOne();
  }
  else if (command == "IMU_READ_LIVE_ON") {
    handleIMULiveOn();
  }
  else if (command == "IMU_READ_LIVE_OFF") {
    handleIMULiveOff();
  }
  else if (command == "IMU_CALIBRATE") {
    handleIMUCalibrate();
  }
  // Comandos ESP-NOW
  else if (command == "ESPNOW_ON") {
    handleESPNowOn();
  }
  else if (command == "ESPNOW_OFF") {
    handleESPNowOff();
  }
  else if (command.startsWith("ESPNOW_PAIR:")) {
    handleESPNowPair(command);
  }
  else if (command == "ESPNOW_STATUS") {
    handleESPNowStatus();
  }
  else if (command.startsWith("GADGET_SEND:")) {
    handleGadgetSend(command);
  }
  // Comandos OTA
  else if (command.startsWith("OTA_START:")) {
    handleOTAStart(command);
  }
  else if (command == "OTA_STOP") {
    handleOTAStop();
  }
  else if (command.length() > 0) {
    Serial.println("ERROR:UNKNOWN_COMMAND:" + command);
  }
  
  Serial.flush();
}

// ===== COMANDOS BÁSICOS (SIN CAMBIOS) =====
void handlePingCommand() {
  Serial.println("SIEV_ESP_OK_v" + String(FIRMWARE_VERSION));
  blinkLED(1, 100);
}

void handleStatusCommand() {
  unsigned long uptime = (millis() - bootTime) / 1000;
  uint32_t freeHeap = ESP.getFreeHeap();
  
  Serial.print("STATUS:OK,UPTIME:");
  Serial.print(uptime);
  Serial.print(",FREE_HEAP:");
  Serial.print(freeHeap);
  Serial.print(",CHIP_ID:");
  Serial.print(ESP.getChipId(), HEX);
  Serial.print(",IMU:");
  Serial.print(imuInitialized ? "OK" : "FAILED");
  Serial.print(",ESPNOW:");
  Serial.print(espnowEnabled ? "ON" : "OFF");
  Serial.print(",OTA:");
  Serial.print(otaEnabled ? "ON" : "OFF");
  Serial.print(",GADGETS:");
  Serial.print(gadgetCount);
  Serial.println();
}

void handleVersionCommand() {
  Serial.print("VERSION:");
  Serial.print(DEVICE_NAME);
  Serial.print(",FW:");
  Serial.print(FIRMWARE_VERSION);
  Serial.print(",SDK:");
  Serial.print(ESP.getSdkVersion());
  Serial.print(",CORE:");
  Serial.print(ESP.getCoreVersion());
  Serial.print(",FLASH:");
  Serial.print(ESP.getFlashChipSize());
  
#ifdef USE_BNO055
  if (imuInitialized) {
    Serial.print(",IMU:");
    Serial.print(imuSensor->getSensorName());
  }
  
  if (espnowEnabled) {
    Serial.print(",MAC:");
    Serial.print(WiFi.macAddress());
  }
#endif
  
  Serial.println();
}

void handleResetCommand() {
  Serial.println("RESET_OK");
  Serial.flush();
  delay(100);
  blinkLED(5, 100);
  ESP.restart();
}

void handleLedCommand(String command, bool turnOn) {
  int colonIndex = command.indexOf(':');
  if (colonIndex == -1) {
    Serial.println("ERROR:INVALID_LED_COMMAND");
    return;
  }
  
  String target = command.substring(colonIndex + 1);
  String action = turnOn ? "LED_ON:" : "LED_OFF:";
  
  if (target == "LEFT") {
    digitalWrite(LEFT_LED_PIN, turnOn ? LOW : HIGH);
    leftLedState = turnOn;
    Serial.println(action + "LEFT");
  }
  else if (target == "RIGHT") {
    digitalWrite(RIGHT_LED_PIN, turnOn ? LOW : HIGH);
    rightLedState = turnOn;
    Serial.println(action + "RIGHT");
  }
  else if (target == "BOTH") {
    digitalWrite(LEFT_LED_PIN, turnOn ? LOW : HIGH);
    digitalWrite(RIGHT_LED_PIN, turnOn ? LOW : HIGH);
    leftLedState = turnOn;
    rightLedState = turnOn;
    Serial.println(action + "BOTH");
  }
  else {
    Serial.println("ERROR:INVALID_LED_TARGET:" + target);
  }
}

// ===== COMANDOS IMU =====
void handleIMUReadOne() {
  if (!imuInitialized) {
    Serial.println("ERROR:IMU_NOT_INITIALIZED");
    return;
  }
  
  if (!imuSensor->isConnected()) {
    Serial.println("ERROR:IMU_NOT_CONNECTED");
    return;
  }
  
  // Leer todos los datos del sensor
  float acc_x, acc_y, acc_z;
  float gyro_x, gyro_y, gyro_z;
  float mag_x, mag_y, mag_z;
  float quat_w, quat_x, quat_y, quat_z;
  float temperature;
  
  bool success = true;
  success &= imuSensor->readAccel(acc_x, acc_y, acc_z);
  success &= imuSensor->readGyro(gyro_x, gyro_y, gyro_z);
  success &= imuSensor->readMag(mag_x, mag_y, mag_z);
  success &= imuSensor->readQuaternion(quat_w, quat_x, quat_y, quat_z);
  temperature = imuSensor->readTemperature();
  
  if (!success) {
    Serial.println("ERROR:IMU_READ_FAILED");
    return;
  }
  
  // Enviar respuesta según protocolo
  Serial.print("IMU:ACC:");
  Serial.print(acc_x, 2); Serial.print(",");
  Serial.print(acc_y, 2); Serial.print(",");
  Serial.print(acc_z, 2); Serial.print(",");
  
  Serial.print("GYRO:");
  Serial.print(gyro_x, 3); Serial.print(",");
  Serial.print(gyro_y, 3); Serial.print(",");
  Serial.print(gyro_z, 3); Serial.print(",");
  
  Serial.print("MAG:");
  Serial.print(mag_x, 1); Serial.print(",");
  Serial.print(mag_y, 1); Serial.print(",");
  Serial.print(mag_z, 1); Serial.print(",");
  
  Serial.print("TEMP:");
  Serial.print(temperature, 1); Serial.print(",");
  
  Serial.print("QUAT:");
  Serial.print(quat_w, 3); Serial.print(",");
  Serial.print(quat_x, 3); Serial.print(",");
  Serial.print(quat_y, 3); Serial.print(",");
  Serial.print(quat_z, 3);
  
  Serial.println();
}

void handleIMULiveOn() {
  if (!imuInitialized) {
    Serial.println("ERROR:IMU_NOT_INITIALIZED");
    return;
  }
  
  if (imuLiveMode) {
    Serial.println("ERROR:IMU_LIVE_ALREADY_ON");
    return;
  }
  
  imuLiveMode = true;
  lastIMURead = millis();
  
  Serial.println("IMU_LIVE:STARTED,RATE:" + String(IMU_SAMPLE_RATE_HZ) + "HZ");
}

void handleIMULiveOff() {
  if (!imuLiveMode) {
    Serial.println("ERROR:IMU_LIVE_NOT_ACTIVE");
    return;
  }
  
  imuLiveMode = false;
  Serial.println("IMU_LIVE:STOPPED");
}

void handleIMUCalibrate() {
  if (!imuInitialized) {
    Serial.println("ERROR:IMU_NOT_INITIALIZED");
    return;
  }
  
  String calibStatus = imuSensor->getCalibrationStatus();
  Serial.println("CALIBRATE:" + calibStatus);
}

// ===== STREAM IMU EN VIVO =====
  for (int i = 0; i < gadgetCount; i++) {
    if (gadgets[i].active) {
      Serial.print("GADGET:");
      Serial.print(macToString(gadgets[i].mac));
      Serial.print(",LAST_SEEN:");
      Serial.print((millis() - gadgets[i].lastSeen) / 1000);
      Serial.println("s");
    }
  }
}

void handleGadgetSend(String command) {
  if (!espnowEnabled) {
    Serial.println("ERROR:ESPNOW_NOT_ENABLED");
    return;
  }
  
  // Formato: GADGET_SEND:AA:BB:CC:DD:EE:FF:DATA
  int firstColon = command.indexOf(':');
  int secondColon = command.indexOf(':', firstColon + 1);
  
  if (firstColon == -1 || secondColon == -1) {
    Serial.println("ERROR:INVALID_GADGET_SEND_FORMAT");
    return;
  }
  
  String macStr = command.substring(firstColon + 1, secondColon);
  String data = command.substring(secondColon + 1);
  
  uint8_t mac[6];
  if (!parseMAC(macStr, mac)) {
    Serial.println("ERROR:INVALID_MAC_ADDRESS");
    return;
  }
  
  // Preparar mensaje
  outgoingMessage.command = CMD_FORWARD_TO_GADGET;
  outgoingMessage.dataLen = data.length();
  strncpy(outgoingMessage.data, data.c_str(), sizeof(outgoingMessage.data) - 1);
  outgoingMessage.data[sizeof(outgoingMessage.data) - 1] = '\0';
  
  // Enviar
  if (esp_now_send(mac, (uint8_t*)&outgoingMessage, sizeof(outgoingMessage)) == 0) {
    Serial.println("GADGET_SENT:" + macStr);
  } else {
    Serial.println("ERROR:GADGET_SEND_FAILED:" + macStr);
  }
}

// ===== COMANDOS OTA =====
void handleOTAStart(String command) {
  // Formato: OTA_START:SSID:PASSWORD
  int firstColon = command.indexOf(':');
  int secondColon = command.indexOf(':', firstColon + 1);
  
  if (firstColon == -1 || secondColon == -1) {
    Serial.println("ERROR:INVALID_OTA_FORMAT");
    return;
  }
  
  String ssid = command.substring(firstColon + 1, secondColon);
  String password = command.substring(secondColon + 1);
  
  startOTA(ssid, password);
}

void handleOTAStop() {
  stopOTA();
}

void startOTA(String ssid, String password) {
  if (otaEnabled) {
    Serial.println("ERROR:OTA_ALREADY_ENABLED");
    return;
  }
  
  // Conectar a WiFi
  WiFi.begin(ssid.c_str(), password.c_str());
  Serial.println("OTA:CONNECTING_WIFI");
  
  unsigned long startTime = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startTime < 10000) {
    delay(500);
    Serial.print(".");
  }
  
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("ERROR:OTA_WIFI_CONNECTION_FAILED");
    return;
  }
  
  Serial.println();
  Serial.println("OTA:WIFI_CONNECTED:" + WiFi.localIP().toString());
  
  // Configurar OTA
  ArduinoOTA.setHostname(OTA_HOSTNAME);
  ArduinoOTA.setPassword(OTA_PASSWORD);
  
  ArduinoOTA.onStart([]() {
    Serial.println("OTA:UPDATE_START");
  });
  
  ArduinoOTA.onEnd([]() {
    Serial.println("OTA:UPDATE_END");
  });
  
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    Serial.printf("OTA:PROGRESS:%u%%\n", (progress * 100) / total);
  });
  
  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("OTA:ERROR[%u]: ", error);
    if (error == OTA_AUTH_ERROR) Serial.println("Auth Failed");
    else if (error == OTA_BEGIN_ERROR) Serial.println("Begin Failed");
    else if (error == OTA_CONNECT_ERROR) Serial.println("Connect Failed");
    else if (error == OTA_RECEIVE_ERROR) Serial.println("Receive Failed");
    else if (error == OTA_END_ERROR) Serial.println("End Failed");
  });
  
  ArduinoOTA.begin();
  otaEnabled = true;
  
  Serial.println("OTA:ENABLED");
}

void stopOTA() {
  if (!otaEnabled) {
    return;
  }
  
  ArduinoOTA.end();
  WiFi.disconnect();
  otaEnabled = false;
  
  Serial.println("OTA:DISABLED");
}
void processIMULiveStream() {
  unsigned long currentTime = millis();
  
  if (currentTime - lastIMURead >= IMU_SAMPLE_INTERVAL_MS) {
    lastIMURead = currentTime;
    
    if (!imuSensor->isConnected()) {
      Serial.println("ERROR:IMU_DISCONNECTED");
      imuLiveMode = false;
      return;
    }
    
    // Leer datos
    float acc_x, acc_y, acc_z;
    float gyro_x, gyro_y, gyro_z;
    float mag_x, mag_y, mag_z;
    float quat_w, quat_x, quat_y, quat_z;
    float temperature;
    
    bool success = true;
    success &= imuSensor->readAccel(acc_x, acc_y, acc_z);
    success &= imuSensor->readGyro(gyro_x, gyro_y, gyro_z);
    success &= imuSensor->readMag(mag_x, mag_y, mag_z);
    success &= imuSensor->readQuaternion(quat_w, quat_x, quat_y, quat_z);
    temperature = imuSensor->readTemperature();
    
    if (!success) {
      Serial.println("ERROR:IMU_LIVE_READ_FAILED");
      return;
    }
    
    // Enviar datos en formato compacto para stream
    Serial.print("LIVE:");
    Serial.print(currentTime); Serial.print(",");
    
    Serial.print(acc_x, 2); Serial.print(",");
    Serial.print(acc_y, 2); Serial.print(",");
    Serial.print(acc_z, 2); Serial.print(",");
    
    Serial.print(gyro_x, 3); Serial.print(",");
    Serial.print(gyro_y, 3); Serial.print(",");
    Serial.print(gyro_z, 3); Serial.print(",");
    
    Serial.print(mag_x, 1); Serial.print(",");
    Serial.print(mag_y, 1); Serial.print(",");
    Serial.print(mag_z, 1); Serial.print(",");
    
    Serial.print(temperature, 1); Serial.print(",");
    
    Serial.print(quat_w, 3); Serial.print(",");
    Serial.print(quat_x, 3); Serial.print(",");
    Serial.print(quat_y, 3); Serial.print(",");
    Serial.print(quat_z, 3);
    
    Serial.println();
  }
}

// ===== FUNCIONES AUXILIARES =====

// ===== ESTRUCTURA DE DATOS ESP-NOW =====
typedef struct {
  uint8_t command;      // Tipo de comando
  uint8_t dataLen;      // Longitud de datos
  char data[248];       // Datos del comando
} ESPNowMessage;

typedef struct {
  uint8_t mac[6];
  bool active;
  unsigned long lastSeen;
  String name;
} GadgetInfo;

// ===== COMANDOS ESP-NOW =====
enum ESPNowCommands {
  CMD_PING = 0x01,
  CMD_DATA = 0x02,
  CMD_STATUS = 0x03,
  CMD_FORWARD_TO_PYTHON = 0x10,
  CMD_FORWARD_TO_GADGET = 0x11
};

// ===== INICIALIZACIÓN ESP-NOW =====
void initESPNowStructures() {
  // Limpiar array de gadgets
  for (int i = 0; i < MAX_GADGETS; i++) {
    memset(gadgets[i].mac, 0, 6);
    gadgets[i].active = false;
    gadgets[i].lastSeen = 0;
    gadgets[i].name = "";
  }
  gadgetCount = 0;
}

bool startESPNow() {
  if (espnowEnabled) {
    return true; // Ya está activado
  }
  
  // Inicializar ESP-NOW
  if (esp_now_init() != 0) {
    Serial.println("ERROR:ESPNOW_INIT_FAILED");
    return false;
  }
  
  // Configurar canal
  esp_now_set_self_role(ESP_NOW_ROLE_COMBO);
  
  // Registrar callbacks
  esp_now_register_recv_cb(onESPNowDataReceived);
  esp_now_register_send_cb(onESPNowDataSent);
  
  espnowEnabled = true;
  Serial.println("DEBUG:ESPNOW_STARTED");
  return true;
}

void stopESPNow() {
  if (!espnowEnabled) {
    return;
  }
  
  esp_now_deinit();
  espnowEnabled = false;
  
  // Limpiar gadgets
  initESPNowStructures();
  
  Serial.println("DEBUG:ESPNOW_STOPPED");
}

// ===== CALLBACKS ESP-NOW =====
void onESPNowDataReceived(uint8_t *mac_addr, uint8_t *data, uint8_t data_len) {
  if (data_len < sizeof(ESPNowMessage)) {
    return;
  }
  
  memcpy(&incomingMessage, data, sizeof(ESPNowMessage));
  
  // Actualizar información del gadget
  updateGadgetInfo(mac_addr);
  
  // Procesar mensaje según comando
  switch (incomingMessage.command) {
    case CMD_PING:
      handleESPNowPing(mac_addr);
      break;
      
    case CMD_FORWARD_TO_PYTHON:
      // Reenviar al Python vía Serial
      Serial.print("GADGET_DATA:");
      Serial.print(macToString(mac_addr));
      Serial.print(":");
      Serial.println(incomingMessage.data);
      break;
      
    case CMD_DATA:
      // Datos generales del gadget
      Serial.print("GADGET_MSG:");
      Serial.print(macToString(mac_addr));
      Serial.print(":");
      Serial.println(incomingMessage.data);
      break;
  }
}

void onESPNowDataSent(uint8_t *mac_addr, uint8_t status) {
  // Opcional: reportar estado de envío
  if (status != 0) {
    Serial.println("ERROR:ESPNOW_SEND_FAILED:" + macToString(mac_addr));
  }
}

void handleESPNowOn() {
  if (startESPNow()) {
    Serial.println("ESPNOW:ON");
  } else {
    Serial.println("ERROR:ESPNOW_START_FAILED");
  }
}

void handleESPNowOff() {
  stopESPNow();
  Serial.println("ESPNOW:OFF");
}

void handleESPNowPair(String command) {
  if (!espnowEnabled) {
    Serial.println("ERROR:ESPNOW_NOT_ENABLED");
    return;
  }
  
  // Extraer MAC address: ESPNOW_PAIR:AA:BB:CC:DD:EE:FF
  int colonPos = command.indexOf(':');
  if (colonPos == -1) {
    Serial.println("ERROR:INVALID_MAC_FORMAT");
    return;
  }
  
  String macStr = command.substring(colonPos + 1);
  uint8_t mac[6];
  
  if (!parseMAC(macStr, mac)) {
    Serial.println("ERROR:INVALID_MAC_ADDRESS");
    return;
  }
  
  // Agregar peer
  if (esp_now_add_peer(mac, ESP_NOW_ROLE_COMBO, ESPNOW_CHANNEL, NULL, 0) != 0) {
    Serial.println("ERROR:ESPNOW_ADD_PEER_FAILED");
    return;
  }
  
  // Agregar a lista de gadgets
  if (addGadget(mac)) {
    Serial.println("ESPNOW_PAIRED:" + macStr);
  } else {
    Serial.println("ERROR:GADGET_LIST_FULL");
  }
}

void handleESPNowStatus() {
  Serial.print("ESPNOW_STATUS:");
  Serial.print(espnowEnabled ? "ON" : "OFF");
  Serial.print(",GADGETS:");
  Serial.print(gadgetCount);
  Serial.print(",MAC:");
  Serial.println(WiFi.macAddress());
  
  // Listar gadgets conectados
  for (int i = 0; i < gadgetCount; i++) {
    if (gadgets[i].active) {
      Serial.print("GADGET:");
      Serial.print(macToString(gadgets[i].mac));
      Serial.print(",LAST_SEEN:");
      Serial.print((millis() - gadgets[i].lastSeen) / 1000);
      Serial.println("s");
    }
  }
}

void handleGadgetSend(String command) {
  if (!espnowEnabled) {
    Serial.println("ERROR:ESPNOW_NOT_ENABLED");
    return;
  }
  
  // Formato: GADGET_SEND:AA:BB:CC:DD:EE:FF:DATA
  int firstColon = command.indexOf(':');
  int secondColon = command.indexOf(':', firstColon + 1);
  
  if (firstColon == -1 || secondColon == -1) {
    Serial.println("ERROR:INVALID_GADGET_SEND_FORMAT");
    return;
  }
  
  String macStr = command.substring(firstColon + 1, secondColon);
  String data = command.substring(secondColon + 1);
  
  uint8_t mac[6];
  if (!parseMAC(macStr, mac)) {
    Serial.println("ERROR:INVALID_MAC_ADDRESS");
    return;
  }
  
  // Preparar mensaje
  outgoingMessage.command = CMD_FORWARD_TO_GADGET;
  outgoingMessage.dataLen = data.length();
  strncpy(outgoingMessage.data, data.c_str(), sizeof(outgoingMessage.data) - 1);
  outgoingMessage.data[sizeof(outgoingMessage.data) - 1] = '\0';
  
  // Enviar
  if (esp_now_send(mac, (uint8_t*)&outgoingMessage, sizeof(outgoingMessage)) == 0) {
    Serial.println("GADGET_SENT:" + macStr);
  } else {
    Serial.println("ERROR:GADGET_SEND_FAILED:" + macStr);
  }
}

// ===== COMANDOS OTA =====
void handleOTAStart(String command) {
  // Formato: OTA_START:SSID:PASSWORD
  int firstColon = command.indexOf(':');
  int secondColon = command.indexOf(':', firstColon + 1);
  
  if (firstColon == -1 || secondColon == -1) {
    Serial.println("ERROR:INVALID_OTA_FORMAT");
    return;
  }
  
  String ssid = command.substring(firstColon + 1, secondColon);
  String password = command.substring(secondColon + 1);
  
  startOTA(ssid, password);
}

void handleOTAStop() {
  stopOTA();
}

void startOTA(String ssid, String password) {
  if (otaEnabled) {
    Serial.println("ERROR:OTA_ALREADY_ENABLED");
    return;
  }
  
  // Conectar a WiFi
  WiFi.begin(ssid.c_str(), password.c_str());
  Serial.println("OTA:CONNECTING_WIFI");
  
  unsigned long startTime = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - startTime < 10000) {
    delay(500);
    Serial.print(".");
  }
  
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("ERROR:OTA_WIFI_CONNECTION_FAILED");
    return;
  }
  
  Serial.println();
  Serial.println("OTA:WIFI_CONNECTED:" + WiFi.localIP().toString());
  
  // Configurar OTA
  ArduinoOTA.setHostname(OTA_HOSTNAME);
  ArduinoOTA.setPassword(OTA_PASSWORD);
  
  ArduinoOTA.onStart([]() {
    Serial.println("OTA:UPDATE_START");
  });
  
  ArduinoOTA.onEnd([]() {
    Serial.println("OTA:UPDATE_END");
  });
  
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    Serial.printf("OTA:PROGRESS:%u%%\n", (progress * 100) / total);
  });
  
  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("OTA:ERROR[%u]: ", error);
    if (error == OTA_AUTH_ERROR) Serial.println("Auth Failed");
    else if (error == OTA_BEGIN_ERROR) Serial.println("Begin Failed");
    else if (error == OTA_CONNECT_ERROR) Serial.println("Connect Failed");
    else if (error == OTA_RECEIVE_ERROR) Serial.println("Receive Failed");
    else if (error == OTA_END_ERROR) Serial.println("End Failed");
  });
  
  ArduinoOTA.begin();
  otaEnabled = true;
  
  Serial.println("OTA:ENABLED");
}

void stopOTA() {
  if (!otaEnabled) {
    return;
  }
  
  ArduinoOTA.end();
  WiFi.disconnect();
  otaEnabled = false;
  
  Serial.println("OTA:DISABLED");
}
void blinkLED(int times, int delayMs) {
  bool originalStateL = digitalRead(LEFT_LED_PIN);
  bool originalStateR = digitalRead(RIGHT_LED_PIN);

  for (int i = 0; i < times; i++) {
    digitalWrite(RIGHT_LED_PIN, LOW);
    digitalWrite(LEFT_LED_PIN, HIGH);
    delay(delayMs);
    digitalWrite(RIGHT_LED_PIN, HIGH);
    digitalWrite(LEFT_LED_PIN, LOW);
    delay(delayMs);
  }
  
  digitalWrite(LEFT_LED_PIN, originalStateL);
  digitalWrite(RIGHT_LED_PIN, originalStateR);
}
