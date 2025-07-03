/*
  SIEV ESP8266 Firmware v1.1.0
  
  Firmware básico para comunicación serie con sistema SIEV
  Responde a comandos básicos: PING, STATUS, VERSION, RESET, LED_ON, LED_OFF
  Firmware con soporte modular para sensores IMU
  Actualmente soporta BNO055, fácilmente intercambiable
  
  Hardware:
  - ESP8266 (cualquier variante)
  - BNO055 IMU conectado por I2C (SDA=GPIO4, SCL=GPIO5)
  - LEDs externos en GPIO12 (LEFT) y GPIO14 (RIGHT)
  - Comunicación serie: 115200 baud, 8N1
  
  Comandos:
  - PING              -> SIEV_ESP_OK_v1.0.0
  - STATUS            -> STATUS:OK,UPTIME:12345,FREE_HEAP:45678
  - VERSION           -> VERSION:SIEV_ESP8266,FW:1.0.0,CHIP:ESP8266,SDK:3.0.2
  - RESET             -> RESET_OK (luego reinicia)
  - LED_ON:LEFT       -> LED_ON:LEFT (enciende LED izquierdo)
  - LED_OFF:LEFT      -> LED_OFF:LEFT (apaga LED izquierdo)
  - LED_ON:RIGHT      -> LED_ON:RIGHT (enciende LED derecho)
  - LED_OFF:RIGHT     -> LED_OFF:RIGHT (apaga LED derecho)
  - LED_ON:BOTH       -> LED_ON:BOTH (enciende ambos LEDs)
  - LED_OFF:BOTH      -> LED_OFF:BOTH (apaga ambos LEDs)
  - IMU_READ_ONE
  - IMU_READ_LIVE_ON
  - IMU_READ_LIVE_OFF
  - IMU_CALIBRATE
  - Autor: Sistema SIEV
  - Fecha: 2025-07-02
  Comandos disponibles:
  - PING, STATUS, VERSION, RESET
  - LED_ON:LEFT/RIGHT/BOTH, LED_OFF:LEFT/RIGHT/BOTH
  - IMU_READ_ONE, IMU_READ_LIVE_ON, IMU_READ_LIVE_OFF, IMU_CALIBRATE
  
  Autor: Sistema SIEV
  Fecha: 2025-07-03
*/

#include <Wire.h>

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
#define FIRMWARE_VERSION "1.1.0"
#define DEVICE_NAME "SIEV_ESP8266"
#define SERIAL_BAUD 115200
#define COMMAND_TIMEOUT 5000
#define MAX_COMMAND_LENGTH 32
#define LEFT_LED_PIN 12   // GPIO12
#define RIGHT_LED_PIN 14  // GPIO14
#define LEFT_LED_PIN 12   // GPIO12
#define RIGHT_LED_PIN 14  // GPIO14

// Configuración I2C
#define SDA_PIN 4  // GPIO4 (D2 en NodeMCU)
#define SCL_PIN 5  // GPIO5 (D1 en NodeMCU)

// Configuración IMU Stream
#define IMU_SAMPLE_RATE_HZ 50
#define IMU_SAMPLE_INTERVAL_MS (1000 / IMU_SAMPLE_RATE_HZ)

// ===== CLASE ABSTRACTA IMU =====
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
  BNO055Sensor() : bno(55) {}
  
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

// ===== SETUP =====
void setup() {
  // Inicializar comunicación serie
  Serial.begin(SERIAL_BAUD);
  while (!Serial) {
    delay(10);
  }
  
  
  // Configurar LEDs izquierdo y derecho
  pinMode(LEFT_LED_PIN, OUTPUT);
  pinMode(RIGHT_LED_PIN, OUTPUT);
  digitalWrite(LEFT_LED_PIN, HIGH);  // LED izquierdo off (HIGH = apagado)
  digitalWrite(RIGHT_LED_PIN, HIGH); // LED derecho off (HIGH = apagado)
  // Configurar LEDs
  pinMode(LEFT_LED_PIN, OUTPUT);
  pinMode(RIGHT_LED_PIN, OUTPUT);
  digitalWrite(LEFT_LED_PIN, HIGH);   // HIGH = apagado
  digitalWrite(RIGHT_LED_PIN, HIGH);  // HIGH = apagado
  
  // Inicializar I2C
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000); // 400kHz
  
  // Inicializar IMU
  initIMU();
  
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
}

// ===== INICIALIZACIÓN IMU =====
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
  

  
  // Pequeña pausa para no saturar
  delay(10);
  // Procesar stream IMU si está activo
  if (imuLiveMode && imuInitialized) {
    processIMULiveStream();
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
  // Comandos LED
  else if (command.startsWith("LED_ON:")) {
    handleLedCommand(command, true);
  }
  else if (command.startsWith("LED_OFF:")) {
    handleLedCommand(command, false);
  }
  // Comando desconocido
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

// ===== CONTROL DE LEDs =====
void handleLedCommand(String command, bool turnOn) {
  // Extraer el parámetro después de los dos puntos
  int colonIndex = command.indexOf(':');
  if (colonIndex == -1) {
    Serial.println("ERROR:INVALID_LED_COMMAND");
    return;
  }
  
  String target = command.substring(colonIndex + 1);
  String action = turnOn ? "LED_ON:" : "LED_OFF:";
  
  if (target == "LEFT") {
    digitalWrite(LEFT_LED_PIN, turnOn ? LOW : HIGH); // LOW = encendido, HIGH = apagado
    Serial.println(action + "LEFT");
  }
  else if (target == "RIGHT") {
    digitalWrite(RIGHT_LED_PIN, turnOn ? LOW : HIGH); // LOW = encendido, HIGH = apagado
    Serial.println(action + "RIGHT");
  }
  else if (target == "BOTH") {
    digitalWrite(LEFT_LED_PIN, turnOn ? LOW : HIGH);
    digitalWrite(RIGHT_LED_PIN, turnOn ? LOW : HIGH);
    Serial.println(action + "BOTH");
  }
  else {
    Serial.println("ERROR:INVALID_LED_TARGET:" + target);
  }
}

// ===== FUNCIONES AUXILIARES =====


void blinkLED(int times, int delayMs) {
  bool originalStateL = digitalRead(LEFT_LED_PIN);
  bool originalStateR = digitalRead(RIGHT_LED_PIN);

  for (int i = 0; i < times; i++) {
    digitalWrite(RIGHT_LED_PIN, LOW);  // LED on
    digitalWrite(LEFT_LED_PIN, HIGH); // LED off

    delay(delayMs);
    digitalWrite(RIGHT_LED_PIN, HIGH); // LED off
    digitalWrite(LEFT_LED_PIN, LOW);  // LED on

    delay(delayMs);
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
  
  digitalWrite(LEFT_LED_PIN, originalStateL); // Restaurar estado
  digitalWrite(RIGHT_LED_PIN, originalStateR); // Restaurar estado

  else {
    Serial.println("ERROR:INVALID_LED_TARGET:" + target);
  }
}

// ===== FUNCIONES DE UTILIDAD =====

void sendDebugInfo() {
  Serial.println("DEBUG:ESP8266_SIEV_FIRMWARE");
  Serial.println("DEBUG:VERSION_" + String(FIRMWARE_VERSION));
  Serial.println("DEBUG:BAUD_" + String(SERIAL_BAUD));
  Serial.println("DEBUG:UPTIME_" + String((millis() - bootTime) / 1000));
  Serial.println("DEBUG:FREE_HEAP_" + String(ESP.getFreeHeap()));
}

// ===== COMANDOS ADICIONALES PARA DESARROLLO =====

void handleDebugCommand() {
  sendDebugInfo();
}

void handleHelpCommand() {
  Serial.println("HELP:AVAILABLE_COMMANDS");
  Serial.println("HELP:PING - Test connectivity");
  Serial.println("HELP:STATUS - System status");
  Serial.println("HELP:VERSION - Firmware info");
  Serial.println("HELP:RESET - Restart device");
  Serial.println("HELP:LED_ON:LEFT/RIGHT/BOTH - Turn on LEDs");
  Serial.println("HELP:LED_OFF:LEFT/RIGHT/BOTH - Turn off LEDs");
  Serial.println("HELP:DEBUG - Debug information");
  Serial.println("HELP:HELP - This message");
}

// ===== MANEJO DE ERRORES =====

void handleSerialError() {
  Serial.println("ERROR:SERIAL_COMMUNICATION");
  blinkLED(10, 50); // Parpadeo rápido de error
}

void handleBufferOverflow() {
  Serial.println("ERROR:BUFFER_OVERFLOW");
  inputBuffer = "";
}

// ===== INFORMACIÓN DEL SISTEMA =====

void printSystemInfo() {
  Serial.println("=== SIEV ESP8266 SYSTEM INFO ===");
  Serial.println("Device: " + String(DEVICE_NAME));
  Serial.println("Firmware: v" + String(FIRMWARE_VERSION));
  Serial.println("Chip ID: 0x" + String(ESP.getChipId(), HEX));
  Serial.println("Flash Size: " + String(ESP.getFlashChipSize()) + " bytes");
  Serial.println("Free Heap: " + String(ESP.getFreeHeap()) + " bytes");
  Serial.println("SDK Version: " + String(ESP.getSdkVersion()));
  Serial.println("Core Version: " + String(ESP.getCoreVersion()));
  Serial.println("Serial: " + String(SERIAL_BAUD) + " baud");
  Serial.println("==============================");
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