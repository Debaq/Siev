#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>

#define VER "0.2.2"
// Definición de pines LED
#define LED_12 12
#define LED_14 14

// Comandos para los LEDs y modos
const String L_12_ON = "L_12_ON";
const String L_12_OFF = "L_12_OFF";
const String L_14_ON = "L_14_ON";
const String L_14_OFF = "L_14_OFF";
const String MODE_EULER = "MODE_EULER";
const String MODE_VHIT = "MODE_VHIT";

// Variables para el serial
String inputString = "";
boolean stringComplete = false;

// Variables para el timing
unsigned long previousMicros = 0;
unsigned long interval = 100000; // 100ms en microsegundos por defecto para Euler
unsigned long vhitInterval = 2000; // 2ms en microsegundos para VHIT (500Hz)

// Variables de control
bool isPaused = false;
bool isCalibrating = false;
bool isVHITMode = false;
float offsetYaw = 0;
float offsetPitch = 0;
float offsetRoll = 0;

// Variables para calibración
unsigned long calTimer = 0;
int calStep = 0;

// Crear objeto BNO055
Adafruit_BNO055 bno = Adafruit_BNO055(55, 0x29);

void setup() {
  Serial.begin(115200);
  
  pinMode(LED_12, OUTPUT);
  pinMode(LED_14, OUTPUT);
  digitalWrite(LED_12, HIGH);
  digitalWrite(LED_14, HIGH);
  
  Wire.begin();
  
  if(!bno.begin()) {
    Serial.println("No se detectó BNO055!");
    while(1);
  }
  
  bno.setExtCrystalUse(true);
  startupSequence();
  
  Serial.println("Controlador listo!");
  Serial.println("Escriba -h para ver los comandos disponibles\n");
}

void startupSequence() {
  for(int i = 0; i < 2; i++) {
    digitalWrite(LED_12, LOW);
    digitalWrite(LED_14, LOW);
    delay(200);
    digitalWrite(LED_12, HIGH);
    digitalWrite(LED_14, HIGH);
    delay(200);
  }
}

void loop() {
  unsigned long currentMicros = micros();
  
  if (stringComplete) {
    processCommand(inputString);
    inputString = "";
    stringComplete = false;
  }
  
  if (isCalibrating) {
    handleCalibration();
  }
  else if (!isPaused) {
    if (currentMicros - previousMicros >= (isVHITMode ? vhitInterval : interval)) {
      previousMicros = currentMicros;
      if (isVHITMode) {
        readAndSendVHITData();
      } else {
        readAndSendEulerData();
      }
    }
  }
}

void handleCalibration() {
  unsigned long currentMillis = millis();
  uint8_t system, gyro, accel, mag;
  bno.getCalibration(&system, &gyro, &accel, &mag);
  
  // Mostrar progreso de calibración cada 2 segundos
  if (currentMillis % 2000 == 0) {
    Serial.print("Progreso: Sys=");
    Serial.print(system);
    Serial.print(" Gyr=");
    Serial.print(gyro);
    Serial.print(" Acc=");
    Serial.print(accel);
    Serial.print(" Mag=");
    Serial.println(mag);
  }
  
  switch(calStep) {
    case 0: // Calibración del giroscopio
      if (currentMillis - calTimer < 3000) {
        if (currentMillis % 1000 == 0) {
          Serial.println("Mantenga el sensor COMPLETAMENTE quieto...");
        }
      } else {
        if (gyro >= 2) {
          Serial.println("\n¡Giroscopio calibrado!");
          Serial.println("\nPaso 2: Calibración del Acelerómetro");
          Serial.println("1. Coloque el sensor en 6 posiciones diferentes");
          Serial.println("2. Mantenga cada posición por 2-3 segundos");
          Serial.println("3. Posiciones sugeridas:");
          Serial.println("   - Apoyado en sus 6 caras");
          Serial.println("   - Como si mirara al frente, arriba, abajo");
          Serial.println("   - Como si mirara a la izquierda y derecha\n");
          calStep++;
          calTimer = currentMillis;
        } else {
          calTimer = currentMillis;
        }
      }
      break;
      
    case 1: // Calibración del acelerómetro
      if (accel >= 2 || currentMillis - calTimer > 20000) {
        Serial.println("\n¡Acelerómetro suficientemente calibrado!");
        Serial.println("\nPaso 3: Calibración del Magnetómetro");
        Serial.println("1. Mueva el sensor en forma de 8");
        Serial.println("2. Movimiento lento y amplio");
        Serial.println("3. Repita el movimiento en diferentes orientaciones\n");
        calStep++;
        calTimer = currentMillis;
      } else if (currentMillis % 3000 == 0) {
        Serial.println("Continúe moviendo a diferentes posiciones...");
      }
      break;
      
    case 2: // Calibración del magnetómetro
      if (mag >= 2 || currentMillis - calTimer > 30000) {
        Serial.println("\n¡Calibración completada!");
        Serial.println("Estado final de calibración:");
        Serial.print("Sistema: "); Serial.println(system);
        Serial.print("Giroscopio: "); Serial.println(gyro);
        Serial.print("Acelerómetro: "); Serial.println(accel);
        Serial.print("Magnetómetro: "); Serial.println(mag);
        
        if (system < 2) {
          Serial.println("\nSugerencia: Puede repetir la calibración");
          Serial.println("para mejorar la precisión si lo desea");
        }
        
        isCalibrating = false;
      } else if (currentMillis % 3000 == 0) {
        Serial.println("Continúe el movimiento en forma de 8...");
      }
      break;
  }
}

void readAndSendEulerData() {
  sensors_event_t event;
  bno.getEvent(&event);
  
  // Aplicar offsets y conversión por sensor invertido
  float yaw = -event.orientation.x - offsetYaw;
  float pitch = -event.orientation.y - offsetPitch;
  float roll = -event.orientation.z - offsetRoll;
  
  // Normalizar ángulos
  yaw = normalizeAngle(yaw);
  pitch = normalizeAngle(pitch);
  roll = normalizeAngle(roll);
  
  Serial.print(yaw);
  Serial.print(",");
  Serial.print(pitch);
  Serial.print(",");
  Serial.println(roll);
}

void readAndSendVHITData() {
  // Obtener aceleración lineal (elimina la gravedad)
  sensors_event_t linearAccelData;
  bno.getEvent(&linearAccelData, Adafruit_BNO055::VECTOR_LINEARACCEL);
  
  // Obtener velocidad angular del giroscopio
  sensors_event_t angVelData;
  bno.getEvent(&angVelData, Adafruit_BNO055::VECTOR_GYROSCOPE);
  
  // Enviar: aX,aY,aZ,gX,gY,gZ
  Serial.print(linearAccelData.acceleration.x);
  Serial.print(",");
  Serial.print(linearAccelData.acceleration.y);
  Serial.print(",");
  Serial.print(linearAccelData.acceleration.z);
  Serial.print(",");
  Serial.print(angVelData.gyro.x);
  Serial.print(",");
  Serial.print(angVelData.gyro.y);
  Serial.print(",");
  Serial.println(angVelData.gyro.z);
}

float normalizeAngle(float angle) {
  while (angle > 180) angle -= 360;
  while (angle < -180) angle += 360;
  return angle;
}

void setZeroPosition() {
  sensors_event_t event;
  bno.getEvent(&event);
  
  offsetYaw = -event.orientation.x;
  offsetPitch = -event.orientation.y;
  offsetRoll = -event.orientation.z;
  
  Serial.println("Posición actual establecida como cero");
}

String getCalibrationStatus() {
  uint8_t system, gyro, accel, mag;
  bno.getCalibration(&system, &gyro, &accel, &mag);
  
  String status = "\nEstado de Calibración (0-3):\n";
  status += "  Sistema: " + String(system);
  status += "  Giroscopio: " + String(gyro);
  status += "  Acelerómetro: " + String(accel);
  status += "  Magnetómetro: " + String(mag) + "\n";
  
  return status;
}

void showHelp() {
  Serial.println("\n=== Comandos Disponibles ===");
  Serial.println("Control de LEDs:");
  Serial.println("  L_12_ON  - Enciende LED 12");
  Serial.println("  L_12_OFF - Apaga LED 12");
  Serial.println("  L_14_ON  - Enciende LED 14");
  Serial.println("  L_14_OFF - Apaga LED 14");
  Serial.println("\nModos de Operación:");
  Serial.println("  MODE_EULER - Modo orientación (yaw,pitch,roll)");
  Serial.println("  MODE_VHIT  - Modo VHIT (aX,aY,aZ,gX,gY,gZ)");
  Serial.println("\nControl de Sensor:");
  Serial.println("  PAUSE    - Pausa/Reanuda lectura del sensor");
  Serial.println("  CAL      - Inicia proceso de calibración guiada");
  Serial.println("  ZERO     - Establece posición actual como cero");
  Serial.println("\nControl de Intervalo:");
  Serial.println("  DELAY_XX - Cambia intervalo en modo Euler (ms)");
  Serial.println("\nFormatos de Datos:");
  Serial.println("  Modo Euler: yaw,pitch,roll (grados)");
  Serial.println("    yaw   = movimiento izquierda-derecha");
  Serial.println("    pitch = movimiento arriba-abajo");
  Serial.println("    roll  = inclinación hacia hombros");
  Serial.println("\n  Modo VHIT: aX,aY,aZ,gX,gY,gZ");
  Serial.println("    aX,aY,aZ = aceleración (m/s²)");
  Serial.println("    gX,gY,gZ = velocidad angular (rad/s)");
  Serial.print("\nVersión: ");
  Serial.println(VER);
  Serial.println(getCalibrationStatus());
  Serial.println("============================\n");
}

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n' || inChar == '\r') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }
}

void processCommand(String command) {
  command.trim();
  
  if (command == "-h") {
    showHelp();
  }
  // Comandos de LED
  else if (command == L_12_ON) {
    digitalWrite(LED_12, LOW);
    Serial.println("LED 12 encendido");
  }
  else if (command == L_12_OFF) {
    digitalWrite(LED_12, HIGH);
    Serial.println("LED 12 apagado");
  }
  else if (command == L_14_ON) {
    digitalWrite(LED_14, LOW);
    Serial.println("LED 14 encendido");
  }
  else if (command == L_14_OFF) {
    digitalWrite(LED_14, HIGH);
    Serial.println("LED 14 apagado");
  }
  // Comandos de modo
  else if (command == MODE_EULER) {
    isVHITMode = false;
    Serial.println("Modo Euler activado");
  }
  else if (command == MODE_VHIT) {
    isVHITMode = true;
    Serial.println("Modo VHIT activado (500Hz)");
  }
  // Otros comandos
  else if (command == "PAUSE") {
    isPaused = !isPaused;
    Serial.println(isPaused ? "Sensor pausado" : "Sensor reactivado");
  }
  else if (command == "CAL") {
    isCalibrating = true;
    calStep = 0;
    calTimer = millis();
    Serial.println("\n=== Iniciando Calibración Guiada ===");
    Serial.println("Paso 1: Calibración del Giroscopio");
    Serial.println("1. Coloque el sensor en una superficie plana");
    Serial.println("2. No lo mueva en absoluto");
    Serial.println("3. Espere unos segundos\n");
  }
  else if (command == "ZERO") {
    setZeroPosition();
  }
  else if (command.startsWith("DELAY_")) {
    if (!isVHITMode) {
      String delayStr = command.substring(6);
      int newDelay = delayStr.toInt();
      if (newDelay > 0) {
        interval = (unsigned long)newDelay * 1000;
        Serial.println("Nuevo intervalo: " + String(newDelay) + "ms");
      }
    } else {
      Serial.println("DELAY no disponible en modo VHIT");
    }
  }
}