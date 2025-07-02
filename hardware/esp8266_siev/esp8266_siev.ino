/*
  SIEV ESP8266 Firmware v1.0.0
  
  Firmware básico para comunicación serie con sistema SIEV
  Responde a comandos básicos: PING, STATUS, VERSION, RESET
  
  Hardware:
  - ESP8266 (cualquier variante)
  - Conectado vía CH340 USB-Serial
  - Comunicación: 115200 baud, 8N1
  
  Comandos:
  - PING    -> SIEV_ESP_OK_v1.0.0
  - STATUS  -> STATUS:OK,UPTIME:12345,FREE_HEAP:45678
  - VERSION -> VERSION:SIEV_ESP8266,FW:1.0.0,CHIP:ESP8266,SDK:3.0.2
  - RESET   -> RESET_OK (luego reinicia)
  
  Autor: Sistema SIEV
  Fecha: 2025-07-02
*/

// ===== CONFIGURACIÓN =====
#define FIRMWARE_VERSION "1.0.0"
#define DEVICE_NAME "SIEV_ESP8266"
#define SERIAL_BAUD 115200
#define COMMAND_TIMEOUT 5000
#define MAX_COMMAND_LENGTH 32
#define HEARTBEAT_LED_PIN LED_BUILTIN
#define HEARTBEAT_INTERVAL 2000

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
  
  // Configurar LED de estado
  pinMode(HEARTBEAT_LED_PIN, OUTPUT);
  digitalWrite(HEARTBEAT_LED_PIN, HIGH); // LED off (inverted on most ESP8266)
  
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
  
  // Heartbeat LED
  handleHeartbeat();
  
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

// ===== FUNCIONES AUXILIARES =====

void handleHeartbeat() {
  unsigned long currentTime = millis();
  
  if (currentTime - lastHeartbeat >= HEARTBEAT_INTERVAL) {
    lastHeartbeat = currentTime;
    ledState = !ledState;
    digitalWrite(HEARTBEAT_LED_PIN, ledState ? LOW : HIGH); // Inverted logic
  }
}

void blinkLED(int times, int delayMs) {
  bool originalState = digitalRead(HEARTBEAT_LED_PIN);
  
  for (int i = 0; i < times; i++) {
    digitalWrite(HEARTBEAT_LED_PIN, LOW);  // LED on
    delay(delayMs);
    digitalWrite(HEARTBEAT_LED_PIN, HIGH); // LED off
    delay(delayMs);
  }
  
  digitalWrite(HEARTBEAT_LED_PIN, originalState); // Restaurar estado
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

// ===== SETUP PARA COMANDOS EXTENDIDOS (OPCIONAL) =====

void setupExtendedCommands() {
  // Aquí se pueden agregar comandos adicionales en el futuro
  // Por ejemplo: calibración, configuración de sensores, etc.
}

/*
  NOTAS DE DESARROLLO:
  
  1. Compila para cualquier ESP8266 (NodeMCU, Wemos D1, etc.)
  2. Configura el IDE en 115200 baud para monitor serie
  3. El LED integrado parpadea cada 2 segundos (heartbeat)
  4. Comandos case-insensitive pero respuestas en mayúsculas
  5. Buffer limitado a 32 caracteres por comando
  6. Timeout de 5 segundos para comandos (no implementado aún)
  
  COMANDOS DE PRUEBA:
  - Enviar "PING" -> debería responder "SIEV_ESP_OK_v1.0.0"
  - Enviar "STATUS" -> info de sistema
  - Enviar "VERSION" -> info detallada
  - Enviar "RESET" -> reinicia el ESP8266
  
  EXPANSIÓN FUTURA:
  - Comandos para sensores específicos
  - Configuración WiFi
  - Comandos de calibración
  - Almacenamiento en EEPROM
  - Comandos de tiempo real
*/