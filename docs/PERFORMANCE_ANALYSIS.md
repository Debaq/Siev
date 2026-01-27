# Análisis de Rendimiento y Ciclo de Vida de Recursos SIEV

**Fecha:** 26 de Enero de 2026
**Sistema Operativo:** Linux
**Contexto:** Diagnóstico de sobrecarga del sistema durante el desarrollo.

Este documento resume el comportamiento de los recursos del sistema a través de las diferentes fases de ejecución de la aplicación SIEV.

## Resumen de Fases

### 1. Fase Limpieza (Baseline)
*   **Estado:** PC en reposo tras ejecutar `pkill` para limpiar procesos antiguos.
*   **CPU:** Mínimo (~5-10% total del sistema, consumido principalmente por herramientas de desarrollo como VS Code y Claude).
*   **RAM:** Estable.
*   **Procesos SIEV:** Ninguno activo.
*   **Conclusión:** El sistema recupera toda su capacidad y no hay procesos "zombies".

### 2. Fase Inicio (Menú / Reposo)
*   **Estado:** Aplicación abierta, esperando interacción del usuario (sin captura de video activa).
*   **Backend (Python):** ~12% CPU (Uso bajo, un solo hilo activo esperando comandos).
*   **Frontend (WebKit/Tauri):** ~5% CPU.
*   **Consumo Total SIEV:** ~20% CPU y ~1GB RAM.
*   **Conclusión:** Consumo ligero y dentro de los parámetros esperados para una aplicación moderna de escritorio en modo desarrollo.

### 3. Fase Procesamiento (Captura Activa)
*   **Estado:** Captura de video iniciada y algoritmos de análisis de pupilas en ejecución.
*   **Backend (Python):** **~515% CPU**.
    *   Esto indica una saturación completa de aproximadamente 5 núcleos físicos.
    *   Es el principal consumidor de recursos debido al procesamiento intensivo de imágenes (visión artificial/redes neuronales).
*   **Frontend (WebKit/Tauri):** ~35% CPU.
    *   Incremento debido al renderizado del feed de video en tiempo real.
    *   Uso de RAM sube a ~830 MB.
*   **Conclusión:** El sistema opera al límite de su capacidad multinúcleo durante el procesamiento. El algoritmo de visión es el cuello de botella principal.

### 4. Fase Cierre (Post-Ejecución)
*   **Estado:** Aplicación cerrada por el usuario.
*   **Procesos SIEV:** Todos los procesos (Python, Tauri, Sidecars) fueron eliminados correctamente.
*   **CPU/RAM:** Retorno a los niveles de la Fase 1.
*   **Conclusión:** El cierre es limpio. No quedaron procesos en segundo plano consumiendo recursos.

## Diagnóstico del Problema Original
La sobrecarga severa experimentada anteriormente se debió a la **acumulación de procesos de la "Fase 3"**. Instancias anteriores del backend de Python no se cerraron correctamente y quedaron ejecutándose en segundo plano al iniciar nuevas instancias, duplicando o triplicando la carga (500% + 500%...), lo que llevó a la saturación total del sistema.

## Solución Implementada
1.  Se verificó que el script de limpieza y los comandos `pkill` funcionan correctamente.
2.  Se desactivó el servicio de indexado `baloo_file` que añadía carga innecesaria.
3.  Se confirmó que el cierre normal de la aplicación ahora termina todos los subprocesos asociados.
