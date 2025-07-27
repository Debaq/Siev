import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple, Optional, Union

class DetectorNistagmo:
    """
    Clase para detectar nistagmos en datos de VNG y calcular la Velocidad de Componente Lenta (VCL).
    
    Esta clase procesa datos oculares para identificar automáticamente los nistagmos,
    marcar sus fases rápidas (sacadas) y lentas (VCL), y calcular sus parámetros.
    """
    
    def __init__(self, 
                 frecuencia_muestreo: float = 100.0,
                 umbral_sacada: float = 25.0,
                 duracion_minima_vcl: float = 0.1,
                 frecuencia_filtro_pb: float = 15.0,
                 frecuencia_filtro_pa: float = 0.5):
        """
        Inicializa el detector de nistagmos con los parámetros de configuración.
        
        Args:
            frecuencia_muestreo: Frecuencia de muestreo de los datos en Hz
            umbral_sacada: Umbral de velocidad para detectar sacadas en °/s
            duracion_minima_vcl: Duración mínima de una VCL en segundos
            frecuencia_filtro_pb: Frecuencia de corte del filtro paso-bajo en Hz
            frecuencia_filtro_pa: Frecuencia de corte del filtro paso-alto en Hz
        """
        self.fs = frecuencia_muestreo
        self.umbral_sacada = umbral_sacada
        self.duracion_minima_vcl = duracion_minima_vcl
        self.freq_pb = frecuencia_filtro_pb
        self.freq_pa = frecuencia_filtro_pa
        
        # Para almacenar resultados
        self.datos_raw = None
        self.datos_filtrados = None
        self.velocidad = None
        self.indices_sacadas = []
        self.segmentos_vcl = []
        
    def procesar_datos(self, datos: Union[List[float], np.ndarray]) -> Dict:
        """
        Procesa una lista de datos oculares para detectar nistagmos.
        
        Args:
            datos: Lista o array de posiciones oculares en grados o píxeles
            
        Returns:
            Diccionario con los resultados del análisis
        """
        self.datos_raw = np.array(datos)
        
        # Paso 1: Filtrar los datos
        self.datos_filtrados = self._filtrar_datos(self.datos_raw)
        
        # Paso 2: Calcular la velocidad (derivada)
        self.velocidad = self._calcular_velocidad(self.datos_filtrados)
        
        # Paso 3: Detectar las sacadas (fase rápida)
        self.indices_sacadas = self._detectar_sacadas(self.velocidad)
        
        # Paso 4: Identificar las VCL (fase lenta)
        self.segmentos_vcl = self._identificar_vcl()
        
        # Recopilar resultados
        resultados = {
            'indices_sacadas': self.indices_sacadas,
            'segmentos_vcl': self.segmentos_vcl,
            'total_nistagmos': len(self.segmentos_vcl),
            'vcl_promedio': np.mean([seg['velocidad'] for seg in self.segmentos_vcl]) if self.segmentos_vcl else 0,
            'velocidad_filtrada': self.velocidad,
            'datos_filtrados': self.datos_filtrados
        }
        
        return resultados
    
    def añadir_datos(self, nuevos_datos: Union[List[float], np.ndarray]) -> Dict:
        """
        Añade nuevos datos a los existentes y realiza el procesamiento.
        Útil para procesamiento en tiempo real.
        
        Args:
            nuevos_datos: Nuevos datos de posición ocular a añadir
            
        Returns:
            Diccionario con los resultados actualizados
        """
        if self.datos_raw is None:
            self.datos_raw = np.array(nuevos_datos)
        else:
            self.datos_raw = np.concatenate([self.datos_raw, nuevos_datos])
        
        # Reprocesar con todos los datos
        return self.procesar_datos(self.datos_raw)
    
    def obtener_marcas_nistagmos(self) -> List[int]:
        """
        Devuelve los índices de inicio de cada nistagmo detectado.
        Un nistagmo se marca en el inicio de la fase rápida (sacada).
        
        Returns:
            Lista de índices donde comienzan los nistagmos
        """
        return self.indices_sacadas
    
    def obtener_vcl(self) -> List[Dict]:
        """
        Devuelve información detallada sobre cada VCL detectada.
        
        Returns:
            Lista de diccionarios con información de cada VCL
        """
        return self.segmentos_vcl
    
    def visualizar(self, ventana_tiempo: Optional[Tuple[int, int]] = None) -> None:
        """
        Genera una visualización de los datos y nistagmos detectados.
        
        Args:
            ventana_tiempo: Tupla opcional (inicio, fin) para visualizar solo un segmento
        """
        if self.datos_raw is None:
            print("No hay datos para visualizar")
            return
        
        # Preparar datos para visualización
        tiempo = np.arange(len(self.datos_raw)) / self.fs
        
        if ventana_tiempo:
            inicio, fin = ventana_tiempo
            slice_idx = slice(int(inicio * self.fs), int(fin * self.fs))
            tiempo_vis = tiempo[slice_idx]
            datos_vis = self.datos_filtrados[slice_idx]
            vel_vis = self.velocidad[slice_idx]
        else:
            tiempo_vis = tiempo
            datos_vis = self.datos_filtrados
            vel_vis = self.velocidad
        
        # Crear figura
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # Graficar posición
        ax1.plot(tiempo_vis, datos_vis, 'b-', label='Posición Ocular')
        ax1.set_ylabel('Posición (grados)')
        ax1.set_title('Detección de Nistagmos')
        ax1.grid(True)
        
        # Marcar VCL en la posición
        for vcl in self.segmentos_vcl:
            if ventana_tiempo is None or (vcl['inicio']/self.fs >= ventana_tiempo[0] and vcl['fin']/self.fs <= ventana_tiempo[1]):
                inicio_t = vcl['inicio'] / self.fs
                fin_t = vcl['fin'] / self.fs
                ax1.axvspan(inicio_t, fin_t, alpha=0.2, color='g')
                # Añadir etiqueta de VCL
                ax1.text(inicio_t + (fin_t - inicio_t)/2, 
                         max(datos_vis) * 0.8,
                         f"{vcl['velocidad']:.1f}°/s", 
                         ha='center')
        
        # Graficar velocidad
        ax2.plot(tiempo_vis, vel_vis, 'r-', label='Velocidad')
        ax2.axhline(y=self.umbral_sacada, color='k', linestyle='--', alpha=0.5, label=f'Umbral ({self.umbral_sacada}°/s)')
        ax2.axhline(y=-self.umbral_sacada, color='k', linestyle='--', alpha=0.5)
        ax2.set_ylabel('Velocidad (°/s)')
        ax2.set_xlabel('Tiempo (s)')
        ax2.grid(True)
        
        # Marcar sacadas
        for idx in self.indices_sacadas:
            if ventana_tiempo is None or (idx/self.fs >= ventana_tiempo[0] and idx/self.fs <= ventana_tiempo[1]):
                t = idx / self.fs
                ax2.axvline(x=t, color='m', linestyle='-', alpha=0.5)
                ax1.axvline(x=t, color='m', linestyle='-', alpha=0.5)
        
        plt.tight_layout()
        plt.show()
    
    def _filtrar_datos(self, datos: np.ndarray) -> np.ndarray:
        """Aplica filtros para eliminar ruido y deriva."""
        # Convertir a numpy array si no lo es
        datos_np = np.array(datos)
        
        # Diseñar filtro paso-bajo (Butterworth)
        b_pb, a_pb = signal.butter(2, self.freq_pb / (self.fs/2), 'low')
        
        # Diseñar filtro paso-alto para eliminar deriva
        b_pa, a_pa = signal.butter(1, self.freq_pa / (self.fs/2), 'high')
        
        # Aplicar filtros en cascada
        datos_pb = signal.filtfilt(b_pb, a_pb, datos_np)
        datos_filtrados = signal.filtfilt(b_pa, a_pa, datos_pb)
        
        return datos_filtrados
    
    def _calcular_velocidad(self, datos: np.ndarray) -> np.ndarray:
        """Calcula la velocidad como la derivada de la posición."""
        # Usar diferencias centrales para calcular la derivada
        velocidad = np.zeros_like(datos)
        velocidad[1:-1] = (datos[2:] - datos[:-2]) * self.fs / 2  # grados/segundo
        
        # Para los extremos usar diferencias hacia adelante/atrás
        velocidad[0] = (datos[1] - datos[0]) * self.fs
        velocidad[-1] = (datos[-1] - datos[-2]) * self.fs
        
        # Suavizar la velocidad ligeramente
        b, a = signal.butter(1, 10 / (self.fs/2), 'low')
        velocidad_suavizada = signal.filtfilt(b, a, velocidad)
        
        return velocidad_suavizada
    
    def _detectar_sacadas(self, velocidad: np.ndarray) -> List[int]:
        """Detecta las sacadas basándose en el umbral de velocidad."""
        # Encontrar puntos donde la velocidad supera el umbral (en cualquier dirección)
        indices_picos = []
        
        # Velocidades positivas (sacadas a la derecha/arriba)
        picos_pos, _ = signal.find_peaks(velocidad, height=self.umbral_sacada, distance=int(0.1*self.fs))
        
        # Velocidades negativas (sacadas a la izquierda/abajo)
        picos_neg, _ = signal.find_peaks(-velocidad, height=self.umbral_sacada, distance=int(0.1*self.fs))
        
        # Combinar y ordenar por tiempo
        indices_picos = np.sort(np.concatenate([picos_pos, picos_neg]))
        
        return indices_picos.tolist()
    
    def _identificar_vcl(self) -> List[Dict]:
        """Identifica las fases lentas entre sacadas consecutivas."""
        segmentos_vcl = []
        
        if len(self.indices_sacadas) < 2:
            return segmentos_vcl
        
        for i in range(len(self.indices_sacadas) - 1):
            idx_inicio = self.indices_sacadas[i]
            idx_fin = self.indices_sacadas[i + 1]
            
            # Encontrar dónde termina realmente la sacada (cuando la velocidad baja del umbral)
            fin_sacada = idx_inicio
            for j in range(idx_inicio, min(idx_fin, idx_inicio + int(0.2 * self.fs))):
                if abs(self.velocidad[j]) < self.umbral_sacada * 0.5:
                    fin_sacada = j
                    break
            
            # Ajustar el inicio de la VCL para que comience después de que termine la sacada
            idx_inicio_vcl = fin_sacada + 1
            
            # Verificar que la duración mínima se cumpla
            duracion = (idx_fin - idx_inicio_vcl) / self.fs
            if duracion < self.duracion_minima_vcl:
                continue
            
            # Calcular la velocidad promedio durante la VCL (pendiente)
            tiempo = np.arange(idx_inicio_vcl, idx_fin) / self.fs
            posicion = self.datos_filtrados[idx_inicio_vcl:idx_fin]
            
            if len(tiempo) < 3:  # Necesitamos al menos 3 puntos para un ajuste lineal confiable
                continue
                
            # Ajuste lineal para calcular la pendiente (VCL)
            try:
                pendiente, interseccion = np.polyfit(tiempo, posicion, 1)
                
                # La pendiente es la velocidad de la VCL
                velocidad_vcl = pendiente
                
                # Solo considerar VCL si la dirección es opuesta a la sacada anterior
                if np.sign(velocidad_vcl) != np.sign(self.velocidad[idx_inicio]):
                    segmentos_vcl.append({
                        'inicio': idx_inicio_vcl,
                        'fin': idx_fin,
                        'velocidad': velocidad_vcl,
                        'duracion': duracion,
                        'amplitud': abs(posicion[-1] - posicion[0])
                    })
            except:
                # En caso de error en el ajuste, omitimos este segmento
                continue
        
        return segmentos_vcl


# Ejemplo de uso:
if __name__ == "__main__":
    # Generar datos sintéticos con nistagmos
    fs = 100  # Hz
    tiempo = np.arange(0, 10, 1/fs)
    
    # Crear una señal con movimientos lentos y rápidos (nistagmos)
    datos = np.zeros_like(tiempo)
    
    # Añadir algunos nistagmos simulados
    for i in range(5):
        # Fase lenta (VCL)
        inicio = 1 + i*2
        fin = inicio + 0.8
        idx_inicio = int(inicio * fs)
        idx_fin = int(fin * fs)
        # Movimiento lento (pendiente negativa)
        datos[idx_inicio:idx_fin] = 5 - (tiempo[idx_inicio:idx_fin] - tiempo[idx_inicio]) * 10
        
        # Fase rápida (sacada)
        inicio_sacada = fin
        fin_sacada = fin + 0.05
        idx_inicio_sacada = int(inicio_sacada * fs)
        idx_fin_sacada = int(fin_sacada * fs)
        # Movimiento rápido (pendiente positiva)
        datos[idx_inicio_sacada:idx_fin_sacada] = datos[idx_inicio_sacada-1] + (tiempo[idx_inicio_sacada:idx_fin_sacada] - tiempo[idx_inicio_sacada-1]) * 200
    
    # Añadir ruido gaussiano
    ruido = np.random.normal(0, 0.2, len(tiempo))
    datos += ruido
    
    # Crear y usar el detector
    detector = DetectorNistagmo(frecuencia_muestreo=fs)
    resultados = detector.procesar_datos(datos)
    
    print(f"Nistagmos detectados: {resultados['total_nistagmos']}")
    print(f"VCL promedio: {resultados['vcl_promedio']:.2f}°/s")
    print(f"Marcas de nistagmos (índices): {detector.obtener_marcas_nistagmos()}")
    
    # Visualizar
    detector.visualizar()