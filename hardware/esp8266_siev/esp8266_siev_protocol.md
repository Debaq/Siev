# ESP8266 SIEV - Protocolo de Comunicación Serial

## Configuración de Comunicación
- **Baudrate:** 115200
- **Formato:** 8N1 (8 bits, sin paridad, 1 bit de stop)
- **Terminador:** `\r\n` (CR+LF)
- **Timeout:** 2 segundos por comando

---

## COMANDOS BÁSICOS

### PING - Test de Conectividad
```
Comando: PING
Respuesta: SIEV_ESP_OK_v1.0.0
Descripción: Verifica que el dispositivo está conectado y funcionando
```

### STATUS - Estado del Sistema
```
Comando: STATUS
Respuesta: STATUS:OK,UPTIME:12345,FREE_HEAP:45678,CHIP_ID:ABC123
Argumentos respuesta:
- OK/ERROR: Estado general del sistema
- UPTIME: Segundos desde el último reinicio
- FREE_HEAP: Memoria libre en bytes
- CHIP_ID: Identificador único del chip (hexadecimal)
```

### VERSION - Información del Firmware
```
Comando: VERSION
Respuesta: VERSION:SIEV_ESP8266,FW:1.0.0,SDK:3.0.2,CORE:2.7.4,FLASH:4194304
Argumentos respuesta:
- SIEV_ESP8266: Nombre del dispositivo
- FW: Versión del firmware
- SDK: Versión del SDK de ESP8266
- CORE: Versión del core de Arduino
- FLASH: Tamaño de memoria flash en bytes
```

### RESET - Reinicio del Dispositivo
```
Comando: RESET
Respuesta: RESET_OK
Descripción: Reinicia el ESP8266 después de confirmar el comando
```

---

## COMANDOS DE CONTROL LED

### LED_ON - Encender LED
```
Comando: LED_ON:LEFT
Comando: LED_ON:RIGHT
Respuesta: LED:LEFT:ON
Respuesta: LED:RIGHT:ON
Argumentos comando:
- LEFT: LED izquierdo
- RIGHT: LED derecho
```

### LED_OFF - Apagar LED
```
Comando: LED_OFF:LEFT
Comando: LED_OFF:RIGHT
Respuesta: LED:LEFT:OFF
Respuesta: LED:RIGHT:OFF
Argumentos comando:
- LEFT: LED izquierdo  
- RIGHT: LED derecho
```

---

## COMANDOS IMU (BNO055/9DOF)

### IMU_READ_ONE - Lectura Única
```
Comando: IMU_READ_ONE
Respuesta: IMU:ACC:1.23,-0.45,9.81,GYRO:0.01,-0.02,0.00,MAG:25.6,-12.3,45.7,TEMP:23.5,QUAT:0.707,0.0,0.0,0.707

Argumentos respuesta:
- ACC: Acelerómetro (m/s²)
  - X: Aceleración eje X
  - Y: Aceleración eje Y  
  - Z: Aceleración eje Z
- GYRO: Giroscopio (rad/s)
  - X: Velocidad angular eje X
  - Y: Velocidad angular eje Y
  - Z: Velocidad angular eje Z
- MAG: Magnetómetro (µT - microteslas)
  - X: Campo magnético eje X
  - Y: Campo magnético eje Y
  - Z: Campo magnético eje Z
- TEMP: Temperatura del sensor (°C)
- QUAT: Quaternion (orientación absoluta)
  - W: Componente escalar
  - X: Componente vector X
  - Y: Componente vector Y
  - Z: Componente vector Z
```

### IMU_READ_LIVE_ON - Iniciar Stream Continuo
```
Comando: IMU_READ_LIVE_ON
Respuesta inicial: IMU_LIVE:STARTED,RATE:50HZ

Luego envía continuamente (cada 20ms a 50Hz):
LIVE:1625123456789,1.23,-0.45,9.81,0.01,-0.02,0.00,25.6,-12.3,45.7,23.5,0.707,0.0,0.0,0.707

Argumentos respuesta inicial:
- STARTED: Confirmación de inicio
- RATE: Frecuencia de muestreo (Hz)

Argumentos stream continuo:
1. Timestamp: Milisegundos desde epoch (Unix timestamp en ms)
2. ACC_X: Aceleración X (m/s²)
3. ACC_Y: Aceleración Y (m/s²)
4. ACC_Z: Aceleración Z (m/s²)
5. GYRO_X: Velocidad angular X (rad/s)
6. GYRO_Y: Velocidad angular Y (rad/s)
7. GYRO_Z: Velocidad angular Z (rad/s)
8. MAG_X: Campo magnético X (µT)
9. MAG_Y: Campo magnético Y (µT)
10. MAG_Z: Campo magnético Z (µT)
11. TEMP: Temperatura (°C)
12. QUAT_W: Quaternion W
13. QUAT_X: Quaternion X
14. QUAT_Y: Quaternion Y
15. QUAT_Z: Quaternion Z
```

### IMU_READ_LIVE_OFF - Detener Stream Continuo
```
Comando: IMU_READ_LIVE_OFF
Respuesta: IMU_LIVE:STOPPED
Descripción: Detiene el envío continuo de datos IMU
```

### IMU_CALIBRATE - Estado de Calibración
```
Comando: IMU_CALIBRATE
Respuesta: CALIBRATE:SYS:2,GYRO:3,ACC:3,MAG:1,STATUS:PARTIAL

Argumentos respuesta:
- SYS: Estado de calibración del sistema (0-3)
- GYRO: Estado de calibración del giroscopio (0-3)
- ACC: Estado de calibración del acelerómetro (0-3)
- MAG: Estado de calibración del magnetómetro (0-3)
- STATUS: Estado general textual

Estados de calibración (0-3):
- 0: Sin calibrar (UNCALIBRATED)
- 1: Calibración mínima (MINIMAL)
- 2: Bien calibrado (GOOD)
- 3: Totalmente calibrado (FULLY_CALIBRATED)

Estados generales:
- UNCALIBRATED: Necesita calibración
- PARTIAL: Parcialmente calibrado
- GOOD: Bien calibrado
- FULLY_CALIBRATED: Completamente calibrado
```

---

## MANEJO DE ERRORES

### Comandos No Reconocidos
```
Comando: COMANDO_INVALIDO
Respuesta: ERROR:UNKNOWN_COMMAND:comando_invalido
```

### Errores de Hardware
```
ERROR:IMU_NOT_FOUND - Sensor IMU no detectado
ERROR:IMU_INIT_FAILED - Fallo al inicializar IMU
ERROR:LED_CONTROL_FAILED - Error controlando LEDs
ERROR:TIMEOUT - Timeout en operación
ERROR:BUFFER_OVERFLOW - Buffer de comando excedido
ERROR:SERIAL_ERROR - Error de comunicación serie
```

### Errores de Parámetros
```
ERROR:INVALID_LED_TARGET:xyz - Target de LED inválido (debe ser LEFT o RIGHT)
ERROR:IMU_LIVE_ALREADY_ON - Stream IMU ya está activo
ERROR:IMU_LIVE_NOT_ACTIVE - Stream IMU no está activo
```

---

## NOTAS DE IMPLEMENTACIÓN

### Frecuencias de Muestreo IMU
- **IMU_READ_ONE:** Lectura bajo demanda
- **IMU_READ_LIVE:** 50Hz por defecto (20ms entre muestras)
- **Máximo recomendado:** 100Hz (10ms) para evitar saturar el puerto serie

### Control de LEDs
- Los LEDs pueden ser independientes (LEFT y RIGHT por separado)
- Estado persiste hasta comando contrario o reinicio
- Confirmación inmediata de cada comando

### Buffer y Timeouts
- Comando máximo: 32 caracteres
- Timeout por comando: 2 segundos
- Buffer circular para stream continuo IMU

### Calibración IMU
- La calibración persiste en la memoria del BNO055
- Se recomienda calibrar en cada sesión para máxima precisión
- El proceso de calibración requiere movimiento del dispositivo