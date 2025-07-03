/*
  SIEV ESP8266 Firmware v1.0.0
  
  Firmware básico para comunicación serie con sistema SIEV
  Responde a comandos básicos: PING, STATUS, VERSION, RESET, LED_ON, LED_OFF
  
  Hardware:
  - ESP8266 (cualquier variante)
  - Conectado vía CH340 USB-Serial
  - Comunicación: 115200 baud, 8N1
  
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
*/

// ===== CONFIGURACIÓN =====
#define FIRMWARE_VERSION "1.0.0"
#define DEVICE_NAME "SIEV_ESP8266"
#define SERIAL_BAUD 115200
#define COMMAND_TIMEOUT 5000
#define MAX_COMMAND_LENGTH 32
#define LEFT_LED_PIN 12   // GPIO12
#define RIGHT_LED_PIN 14  // GPIO14

// ===== VARIABLES GLOBALES =====
String inputBuffer = "";
unsigned long lastHeartbeat = 0;
unsigned long bootTime = 0;
bool ledState = false;

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
  
  // Guardar tiempo de inicio
  bootTime = millis();
  
  // Mensaje de inicio
  delay(100); // Pequeña pausa para estabilizar
  Serial.println("SYSTEM:SIEV_ESP8266_READY_v" + String(FIRMWARE_VERSION));
  Serial.flush();
  
  // Reservar buffer para comandos
  inputBuffer.reserve(MAX_COMMAND_LENGTH);
  
  // LED de confirmación de inicio
  blinkLED(3, 200);
}

// ===== LOOP PRINCIPAL =====
void loop() {
  // Procesar comandos serie
  processSerialCommands();
  

  
  // Pequeña pausa para no saturar
  delay(10);
}

// ===== PROCESAMIENTO DE COMANDOS =====
void processSerialCommands() {
  while (Serial.available()) {
    char receivedChar = Serial.read();
    
    // Detectar fin de comando (CR, LF, o ambos)
    if (receivedChar == '\r' || receivedChar == '\n') {
      if (inputBuffer.length() > 0) {
        processCommand(inputBuffer);
        inputBuffer = "";
      }
    }
    // Agregar carácter al buffer
    else if (inputBuffer.length() < MAX_COMMAND_LENGTH - 1) {
      inputBuffer += receivedChar;
    }
    // Buffer overflow - limpiar
    else {
      inputBuffer = "";
      Serial.println("ERROR:COMMAND_TOO_LONG");
    }
  }
}

// ===== PROCESAR COMANDO INDIVIDUAL =====
void processCommand(String command) {
  // Convertir a mayúsculas y limpiar espacios
  command.trim();
  command.toUpperCase();
  
  // Comando PING
  if (command == "PING") {
    handlePingCommand();
  }
  // Comando STATUS
  else if (command == "STATUS") {
    handleStatusCommand();
  }
  // Comando VERSION
  else if (command == "VERSION") {
    handleVersionCommand();
  }
  // Comando RESET
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
  else if (command.length() > 0) {
    Serial.println("ERROR:UNKNOWN_COMMAND:" + command);
  }
  
  Serial.flush();
}

// ===== COMANDOS ESPECÍFICOS =====

void handlePingCommand() {
  Serial.println("SIEV_ESP_OK_v" + String(FIRMWARE_VERSION));
  blinkLED(1, 100); // Confirmación visual
}

void handleStatusCommand() {
  unsigned long uptime = (millis() - bootTime) / 1000; // segundos
  uint32_t freeHeap = ESP.getFreeHeap();
  
  Serial.print("STATUS:OK,UPTIME:");
  Serial.print(uptime);
  Serial.print(",FREE_HEAP:");
  Serial.print(freeHeap);
  Serial.print(",CHIP_ID:");
  Serial.print(ESP.getChipId(), HEX);
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
  Serial.println();
}

void handleResetCommand() {
  Serial.println("RESET_OK");
  Serial.flush();
  delay(100);
  
  // Parpadeo rápido antes de reiniciar
  blinkLED(5, 100);
  
  // Reinicio del ESP8266
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
  }
  
  digitalWrite(LEFT_LED_PIN, originalStateL); // Restaurar estado
  digitalWrite(RIGHT_LED_PIN, originalStateR); // Restaurar estado

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
}

/*
  NOTAS DE DESARROLLO:
  
  1. Compila para cualquier ESP8266 (NodeMCU, Wemos D1, etc.)
  2. Configura el IDE en 115200 baud para monitor serie
  3. El LED integrado parpadea cada 2 segundos (heartbeat)
  4. Comandos case-insensitive pero respuestas en mayúsculas
  5. Buffer limitado a 32 caracteres por comando
  6. LEDs externos conectados a GPIO12 (LEFT) y GPIO14 (RIGHT)
  7. Lógica invertida: LOW = encendido, HIGH = apagado
  
  COMANDOS DE PRUEBA:
  - Enviar "PING" -> debería responder "SIEV_ESP_OK_v1.0.0"
  - Enviar "STATUS" -> info de sistema
  - Enviar "VERSION" -> info detallada
  - Enviar "RESET" -> reinicia el ESP8266
  - Enviar "LED_ON:LEFT" -> enciende el LED izquierdo
  - Enviar "LED_OFF:LEFT" -> apaga el LED izquierdo
  - Enviar "LED_ON:RIGHT" -> enciende el LED derecho
  - Enviar "LED_OFF:RIGHT" -> apaga el LED derecho
  - Enviar "LED_ON:BOTH" -> enciende ambos LEDs
  - Enviar "LED_OFF:BOTH" -> apaga ambos LEDs
  
  EXPANSIÓN FUTURA:
  - Comandos para sensores específicos
  - Configuración WiFi
  - Comandos de calibración
  - Almacenamiento en EEPROM
  - Comandos de tiempo real
*/
