# SIEV - Sistema Integrado de Evaluación Vestibular

<div align="center">

![Version](https://img.shields.io/badge/version-0.0.1--alpha-blue)
![Python](https://img.shields.io/badge/python-3.x-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-alpha-yellow)

**Sistema de Videonistagmografía (VNG) para diagnóstico médico y optométrico**

[Características](#características) • [Instalación](#instalación) • [Uso](#uso) • [Hardware](#hardware-requerido) • [Documentación](#documentación)

</div>

---

## 📋 Descripción

SIEV es un sistema avanzado de **Videonistagmografía (VNG)** diseñado para el análisis de movimientos oculares y detección de nistagmo en entornos clínicos. Combina visión por computadora, procesamiento de señales en tiempo real e integración de hardware especializado para proporcionar una solución completa de diagnóstico vestibular y neurológico.

### ¿Qué es la Videonistagmografía?

La VNG es una técnica de diagnóstico médico que registra y analiza los movimientos oculares para detectar trastornos del sistema vestibular, problemas de equilibrio y condiciones neurológicas. SIEV automatiza este proceso utilizando detección de pupilas basada en IA y análisis algorítmico avanzado.

---

## ✨ Características

### 🔬 Capacidades Diagnósticas

- **Seguimiento Ocular en Tiempo Real**: Detección precisa de la posición de la pupila usando YOLOv8
- **Detección Automática de Nistagmo**: Algoritmos especializados para identificar movimientos oculares involuntarios
- **Cálculo de VCL**: Medición de la Velocidad del Componente Lento del nistagmo
- **Sistema de Calibración Multi-punto**: Conversión precisa de píxeles a grados de movimiento ocular
- **Filtrado Kalman**: Procesamiento avanzado de señales para seguimiento suave y preciso

### 📊 Protocolos de Prueba

- **Pruebas Calóricas**: OD/OI 44°C y 30°C (estimulación térmica)
- **Seguimiento Lento**: Análisis de movimientos de persecución suave
- **Nistagmo Optocinético**: Evaluación de respuestas optocinéticas
- **Sacadas**: Pruebas de movimientos oculares sacádicos
- **Nistagmo Espontáneo**: Detección de nistagmo en reposo

### 💾 Gestión de Datos

- **Perfiles de Pacientes**: Sistema completo de gestión de usuarios/pacientes
- **Almacenamiento Persistente**: Base de datos de resultados y datos históricos
- **Grabación de Video**: Captura de sesiones de prueba para análisis posterior
- **Generación de Informes PDF**: Reportes clínicos profesionales con análisis y recomendaciones

### 📈 Visualización y Análisis

- **Gráficos en Tiempo Real**: Visualización simultánea de posición, velocidad y aceleración
- **Widget de Triple Gráfico**: Análisis de tres flujos de datos simultáneos
- **Detección de Parpadeos**: Identificación automática y marcado de parpadeos
- **Gráficos Calóricos Especializados**: Visualización específica para análisis de pruebas calóricas
- **Calculadora Clínica**: Calculadora de hipodensidad y preponderancia direccional

### 🔧 Integración de Hardware

- **Comunicación Serial**: Interfaz con microcontroladores ESP8266/ESP32C3
- **Procesamiento de IMU**: Integración con sensores inerciales (BNO055/ICM20948)
- **Control de LEDs**: Gestión de LEDs infrarrojos para puntos de calibración
- **Soporte Multi-cámara**: Compatible con múltiples resoluciones y fuentes de video

---

## 🛠️ Tecnologías

### Lenguajes y Frameworks

- **Python 3.x**: Lenguaje principal
- **PySide6 (Qt6)**: Framework de interfaz gráfica
- **C/Arduino**: Firmware para microcontroladores

### Librerías Clave

#### Visión por Computadora e IA
- **OpenCV 4.11**: Procesamiento de imágenes y captura de video
- **Ultralytics 8.3**: YOLOv8 para detección de ojos
- **PyTorch 2.0+**: Framework de aprendizaje profundo

#### Computación Científica
- **NumPy 1.24+**: Computación numérica
- **SciPy 1.10+**: Procesamiento de señales y algoritmos científicos
- **Matplotlib 3.7+**: Visualización de datos
- **pyqtgraph 0.13**: Gráficos en tiempo real

#### Procesamiento de Datos
- **Polars 0.20+**: Manipulación rápida de datos

#### Hardware
- **PySerial 3.5+**: Comunicación por puerto serial

---

## 📦 Instalación

### Requisitos del Sistema

- **Sistema Operativo**: Linux (con soporte V4L2) o Windows
- **Python**: 3.x
- **Memoria RAM**: Mínimo 4GB, recomendado 8GB
- **Procesador**: Intel Core i5 o superior (para procesamiento en tiempo real)
- **Cámara USB**: Compatible con el sistema operativo
- **Puerto Serial**: Para comunicación con hardware

### Instalación con Micromamba

```bash
# Clonar el repositorio
git clone https://github.com/Debaq/Siev.git
cd Siev

# Crear y activar entorno conda
micromamba create -n vng python=3.x
micromamba activate vng

# Instalar dependencias
pip install -r requirements.txt
```

### Instalación Manual

```bash
# Instalar dependencias principales
pip install PySide6==6.8.0.2
pip install opencv-python==4.11.0.86
pip install ultralytics==8.3.161
pip install pyqtgraph==0.13.7
pip install numpy scipy matplotlib
pip install torch torchvision
pip install pyserial polars

# Instalar todas las dependencias
pip install -r requirements.txt
```

---

## 🚀 Uso

### Iniciar la Aplicación

#### Usando el script de inicio:
```bash
./siev.sh
```

#### Inicio manual:
```bash
cd ~/Siev
micromamba activate vng
python src/main.py
```

### Flujo de Trabajo Básico

1. **Iniciar la Aplicación**: Ejecutar SIEV usando uno de los métodos anteriores
2. **Conectar Hardware**: Asegurarse de que los dispositivos ESP32C3 estén conectados
3. **Crear/Seleccionar Paciente**: Gestionar perfiles de pacientes desde el menú
4. **Calibrar Sistema**:
   - Ejecutar calibración de puntos IR
   - Verificar detección de pupilas
5. **Seleccionar Protocolo**: Elegir el tipo de prueba a realizar
6. **Ejecutar Prueba**:
   - Iniciar grabación
   - Presentar estímulos según protocolo
   - Monitorear datos en tiempo real
7. **Analizar Resultados**: Revisar gráficos y datos de nistagmo
8. **Generar Reporte**: Crear informe PDF para el paciente

### Configuración de Cámara

El sistema detecta automáticamente las capacidades de la cámara. Para configuración manual:

```python
# En el archivo de configuración o UI
resoluciones_soportadas = [
    (1920, 1080),  # Full HD
    (1280, 720),   # HD
    (640, 480)     # VGA
]
```

---

## 🔌 Hardware Requerido

### Componentes Principales

| Componente | Cantidad | Descripción |
|------------|----------|-------------|
| **ESP32C3** | 4 | Microcontroladores principales |
| **BNO055 / ICM20948** | 1 | Sensor IMU de 9 ejes |
| **Cámara USB** | 1-2 | Captura de movimientos oculares |
| **LEDs Infrarrojos** | Varios | Calibración y iluminación (760nm) |
| **Filtros IR** | 2 | Filtros pasa-largo de 760nm |
| **Hub USB GL852** | 1 | Controlador de hub USB |

### Configuración de Hardware

**Comunicación Serial:**
- Baudrate: 115200
- Formato: 8N1 (8 bits, sin paridad, 1 bit de parada)
- Terminador: CR+LF (`\r\n`)
- Timeout: 2 segundos

**Protocolo de Comandos:** Ver `hardware/esp8266_siev/esp8266_siev_protocol.md`

### Modelo de Costo

Consultar el archivo `BOM.md` para una lista completa de materiales y costos estimados (en pesos argentinos).

---

## 📁 Estructura del Proyecto

```
Siev/
├── src/                        # Código fuente principal
│   ├── main.py                # Punto de entrada con auto-actualización
│   ├── VERSION.json           # Control de versiones
│   ├── managers/              # Gestores de alto nivel
│   │   ├── data_manager.py    # Gestión de datos de pacientes
│   │   ├── hardware_manager.py # Control de hardware
│   │   ├── test_manager.py    # Gestión de protocolos de prueba
│   │   └── video_manager.py   # Captura y reproducción de video
│   ├── models/                # Modelos de datos y ML
│   │   ├── data_models.py     # Estructuras de datos
│   │   └── siev_vng_r01.pt    # Modelo YOLOv8 pre-entrenado
│   ├── ui/                    # Interfaz de usuario
│   │   ├── main_window.py     # Ventana principal
│   │   ├── dialogs/           # Diálogos y ventanas modales
│   │   └── views/             # Vistas especializadas
│   └── utils/                 # Utilidades y procesamiento
│       ├── CalibrationManager.py     # Gestión de calibración
│       ├── EyeDataProcessor.py       # Filtrado Kalman
│       ├── DetectorNistagmo.py       # Detección de nistagmo
│       ├── SerialHandler.py          # Comunicación serial
│       ├── graphing/                 # Módulos de gráficos
│       └── video/                    # Procesamiento de video
├── hardware/                   # Firmware y hardware
│   └── esp8266_siev/          # Firmware ESP8266/ESP32C3
├── requirements.txt            # Dependencias Python
├── BOM.md                      # Lista de materiales
└── siev.sh                     # Script de inicio
```

---

## 📖 Documentación

### Documentación Disponible

- **[BOM.md](BOM.md)**: Lista de materiales y costos
- **[Protocolo Serial](hardware/esp8266_siev/esp8266_siev_protocol.md)**: Especificación del protocolo de comunicación
- **Código**: Documentación inline en docstrings

### Características Técnicas Clave

#### Sistema de Calibración
- Calibración de dos puntos (LED izquierdo y derecho)
- Conversión píxel a grados de movimiento ocular
- Calibración automática de hardware

#### Detección de Ojos
- Modelo: YOLOv8 personalizado (`siev_vng_r01.pt`)
- Entrada: Frames de video en tiempo real
- Salida: Coordenadas de pupila (x, y) con confianza

#### Procesamiento de Señales
- **Filtro Kalman**: Seguimiento suave con modelo de aceleración
- **Frecuencia de Muestreo**: 50Hz para datos de IMU
- **Sincronización**: Basada en timestamps

#### Grabación y Análisis
- Duración configurable (2-5 minutos por sesión)
- Grabación simultánea de video y datos
- Análisis post-procesamiento disponible

---

## 🔄 Sistema de Actualización

SIEV incluye un sistema de auto-actualización automática:

- Verificación de actualizaciones al inicio
- Descarga automática desde GitHub
- Actualización de dependencias
- Timeout de 15 segundos para verificación

### CI/CD

- **GitHub Actions**: Bump automático de versión en push a development
- **Gestión de Versiones**: Almacenado en `src/VERSION.json`
- **Despliegue Alpha**: Script `update_alpha.py` para actualizaciones

---

## 🧪 Desarrollo

### Entorno de Desarrollo

```bash
# Activar entorno
micromamba activate vng

# Ejecutar en modo desarrollo
python src/main.py

# Ejecutar tests (si están disponibles)
pytest tests/
```

### Arquitectura

El proyecto sigue varios patrones de diseño:

- **Patrón Manager**: Gestores separados por subsistema
- **Signal/Slot (Qt)**: Comunicación asíncrona entre componentes
- **Threading**: Operaciones de larga duración en hilos separados
- **Observer**: Actualizaciones de UI basadas en eventos
- **State Machine**: Gestión de estados de prueba y calibración

---

## 🤝 Contribución

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crear una rama de feature (`git checkout -b feature/nueva-caracteristica`)
3. Commit de cambios (`git commit -m 'Agregar nueva característica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Abrir un Pull Request

### Ramas Principales

- `main`: Versión estable de producción
- `development`: Desarrollo activo
- `claude/*`: Ramas de feature automatizadas

---

## 📄 Licencia

Este proyecto está bajo licencia MIT. Ver el archivo `LICENSE` para más detalles.

---

## 👥 Autores

**Proyecto SIEV** - Sistema de diagnóstico VNG de código abierto

---

## 🙏 Agradecimientos

- Ultralytics por el framework YOLOv8
- Qt/PySide6 por el excelente framework de UI
- Comunidad de OpenCV
- Todos los contribuidores del proyecto

---

## 📞 Soporte

Para reportar bugs o solicitar características:
- Abrir un [Issue en GitHub](https://github.com/Debaq/Siev/issues)
- Consultar la documentación en el directorio del proyecto

---

## 🚧 Estado del Proyecto

**Versión Actual**: 0.0.1-alpha

Este proyecto está en fase **ALPHA**. Características en desarrollo activo:
- [ ] Estabilización de detección de nistagmo
- [ ] Mejoras en generación de reportes PDF
- [ ] Optimización de rendimiento en tiempo real
- [ ] Interfaz de usuario mejorada
- [ ] Tests automatizados
- [ ] Documentación completa de API

---

<div align="center">

**SIEV** - Diagnóstico vestibular accesible y de código abierto

⭐ Si este proyecto te es útil, considera darle una estrella en GitHub ⭐

</div>
