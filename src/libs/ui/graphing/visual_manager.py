import numpy as np
import pyqtgraph as pg
from typing import List, Dict, Optional, Tuple
import time


class OptimizedVisualManager:
    """
    Gestor visual optimizado que maneja la representación eficiente de datos
    en los gráficos, con técnicas avanzadas de rendering y cache.
    """
    
    def __init__(self, window_size=60.0, max_visible_points=2000):
        """
        Args:
            window_size: Tamaño de la ventana visible en segundos
            max_visible_points: Máximo número de puntos visibles simultáneamente
        """
        self.window_size = window_size
        self.max_visible_points = max_visible_points
        
        # Control de auto-scroll
        self.auto_scroll = True
        self._updating_range = False
        
        # Cache de renderizado
        self._render_cache = {}
        self._cache_validity_time = 0.1  # 100ms
        self._last_cache_time = 0
        
        # Configuración de optimización dinámica
        self.optimization_config = {
            'adaptive_downsampling': True,
            'smart_range_updates': True,
            'cache_enabled': True,
            'blink_region_limit': 50,
            'performance_mode': False
        }
        
        # Estadísticas de rendering
        self.render_stats = {
            'total_renders': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_render_time': 0.0,
            'last_render_time': 0.0
        }
        
        # Estado anterior para optimización delta
        self.last_data_hash = None
        self.last_visible_range = None
    
    def update_plots(self, plots: List, curves: List, data: Dict, 
                    blink_detector=None, current_time: Optional[float] = None) -> bool:
        """
        Actualiza los gráficos de manera optimizada.
        
        Args:
            plots: Lista de objetos PlotWidget
            curves: Lista de objetos PlotDataItem (6 curvas: 2 por gráfico)
            data: Diccionario con datos a visualizar
            blink_detector: Detector de parpadeos opcional
            current_time: Tiempo actual
            
        Returns:
            True si la actualización fue exitosa
        """
        if not data or len(data.get('timestamps', [])) == 0:
            return False
        
        start_time = time.time()
        
        try:
            # Verificar si necesitamos actualización
            if not self._should_update(data, current_time):
                self.render_stats['cache_hits'] += 1
                return True
            
            self.render_stats['cache_misses'] += 1
            
            # Obtener datos visibles optimizados
            visible_data = self._get_visible_data(data, current_time)
            
            if len(visible_data['timestamps']) == 0:
                return False
            
            # Aplicar auto-scroll si está activo
            if self.auto_scroll:
                self._apply_auto_scroll(plots, visible_data['timestamps'])
            
            # Actualizar curvas de manera eficiente
            self._update_curves_optimized(curves, visible_data)
            
            # Actualizar regiones de parpadeo
            if blink_detector:
                self._update_blink_regions_optimized(plots, blink_detector, visible_data)
            
            # Actualizar cache y estadísticas
            self._update_cache(data, visible_data, current_time)
            self._update_stats(start_time)
            
            return True
            
        except Exception as e:
            print(f"Error en update_plots: {e}")
            return False
    
    def _should_update(self, data: Dict, current_time: Optional[float]) -> bool:
        """
        Determina si se necesita actualizar la visualización.
        
        Args:
            data: Datos actuales
            current_time: Tiempo actual
            
        Returns:
            True si se necesita actualización
        """
        if not self.optimization_config['cache_enabled']:
            return True
        
        # Verificar tiempo de cache
        if current_time is None:
            current_time = time.time()
        
        time_since_cache = current_time - self._last_cache_time
        if time_since_cache < self._cache_validity_time:
            # Cache aún válido, verificar si los datos cambiaron significativamente
            current_hash = self._calculate_data_hash(data)
            if current_hash == self.last_data_hash:
                return False  # Datos no han cambiado
        
        return True  # Necesita actualización
    
    def _get_visible_data(self, data: Dict, current_time: Optional[float]) -> Dict:
        """
        Obtiene solo los datos visibles en la ventana actual.
        
        Args:
            data: Datos completos
            current_time: Tiempo actual
            
        Returns:
            Diccionario con datos visibles optimizados
        """
        timestamps = data['timestamps']
        
        if current_time is None:
            current_time = timestamps[-1] if len(timestamps) > 0 else time.time()
        
        # Calcular ventana visible
        if self.auto_scroll:
            end_time = current_time
            start_time = max(0, end_time - self.window_size)
        else:
            # Usar rango actual de la vista (se establecería desde el plot)
            start_time = current_time - self.window_size
            end_time = current_time
        
        # Encontrar índices visibles de manera eficiente
        if isinstance(timestamps, np.ndarray):
            mask = (timestamps >= start_time) & (timestamps <= end_time)
            indices = np.where(mask)[0]
        else:
            # Fallback para listas
            indices = [i for i, t in enumerate(timestamps) if start_time <= t <= end_time]
            indices = np.array(indices)
        
        if len(indices) == 0:
            return self._empty_visible_data()
        
        # Aplicar downsampling si hay demasiados puntos
        if len(indices) > self.max_visible_points and self.optimization_config['adaptive_downsampling']:
            indices = self._downsample_indices(indices)
        
        # Extraer datos visibles
        visible_data = {}
        for key, values in data.items():
            if isinstance(values, np.ndarray):
                visible_data[key] = values[indices]
            else:
                # Fallback para listas
                visible_data[key] = np.array([values[i] for i in indices])
        
        return visible_data
    
    def _downsample_indices(self, indices: np.ndarray) -> np.ndarray:
        """
        Aplica downsampling inteligente a los índices.
        
        Args:
            indices: Array de índices originales
            
        Returns:
            Array de índices downsampled
        """
        if len(indices) <= self.max_visible_points:
            return indices
        
        # Estrategia de downsampling: mantener densidad uniforme
        step = len(indices) // self.max_visible_points
        downsampled = indices[::step]
        
        # Asegurar que el último punto esté incluido
        if len(downsampled) > 0 and downsampled[-1] != indices[-1]:
            downsampled = np.append(downsampled, indices[-1])
        
        return downsampled
    
    def _update_curves_optimized(self, curves: List, visible_data: Dict):
        """
        Actualiza las curvas de manera optimizada.
        
        Args:
            curves: Lista de curvas a actualizar
            visible_data: Datos visibles
        """
        timestamps = visible_data['timestamps']
        
        # Mapeo de curvas a datos (orden específico para 3 gráficos x 2 ojos)
        curve_data_mapping = [
            'left_eye_x',    # Gráfico 0, ojo izquierdo X
            'right_eye_x',   # Gráfico 0, ojo derecho X
            'left_eye_y',    # Gráfico 1, ojo izquierdo Y
            'right_eye_y',   # Gráfico 1, ojo derecho Y
            'imu_x',         # Gráfico 2, IMU X (como ojo izquierdo)
            'imu_y'          # Gráfico 2, IMU Y (como ojo derecho)
        ]
        
        # Actualizar cada curva
        for i, (curve, data_key) in enumerate(zip(curves, curve_data_mapping)):
            if data_key in visible_data and len(visible_data[data_key]) > 0:
                try:
                    # Verificar que los datos son válidos
                    y_data = visible_data[data_key]
                    
                    # Filtrar NaN e infinitos
                    valid_mask = np.isfinite(y_data)
                    if np.any(valid_mask):
                        valid_timestamps = timestamps[valid_mask]
                        valid_y_data = y_data[valid_mask]
                        
                        # Actualizar curva de manera eficiente
                        curve.setData(valid_timestamps, valid_y_data)
                    else:
                        # Todos los datos son inválidos, limpiar curva
                        curve.setData([], [])
                        
                except Exception as e:
                    print(f"Error actualizando curva {i}: {e}")
                    curve.setData([], [])
            else:
                # No hay datos para esta curva
                curve.setData([], [])
    
    def _update_blink_regions_optimized(self, plots: List, blink_detector, visible_data: Dict):
        """
        Actualiza las regiones de parpadeo de manera optimizada.
        
        Args:
            plots: Lista de gráficos
            blink_detector: Detector de parpadeos
            visible_data: Datos visibles
        """
        try:
            # Obtener regiones de parpadeo
            if hasattr(blink_detector, 'get_blink_regions'):
                left_regions, right_regions = blink_detector.get_blink_regions()
            else:
                # Fallback: detectar desde estados en datos visibles
                left_regions, right_regions = self._detect_blink_regions_from_data(visible_data)
            
            # Limitar número de regiones para performance
            max_regions = self.optimization_config['blink_region_limit']
            if len(left_regions) > max_regions:
                left_regions = left_regions[-max_regions:]
            if len(right_regions) > max_regions:
                right_regions = right_regions[-max_regions:]
            
            # Aplicar regiones a todos los gráficos
            for plot in plots:
                # Limpiar regiones existentes de manera eficiente
                items_to_remove = []
                for item in plot.items():
                    if isinstance(item, pg.LinearRegionItem):
                        items_to_remove.append(item)
                
                for item in items_to_remove:
                    plot.removeItem(item)
                
                # Añadir nuevas regiones
                self._add_blink_regions_to_plot(plot, left_regions, right_regions)
                
        except Exception as e:
            print(f"Error actualizando regiones de parpadeo: {e}")
    
    def _add_blink_regions_to_plot(self, plot, left_regions: List, right_regions: List):
        """
        Añade regiones de parpadeo a un gráfico específico.
        
        Args:
            plot: Gráfico donde añadir las regiones
            left_regions: Regiones del ojo izquierdo
            right_regions: Regiones del ojo derecho
        """
        # Regiones del ojo izquierdo (azul)
        for start, end in left_regions:
            if end > start and (end - start) > 0.001:  # Validar región
                region = pg.LinearRegionItem(
                    values=[start, end],
                    brush=pg.mkBrush(0, 0, 255, 50),
                    movable=False
                )
                plot.addItem(region)
        
        # Regiones del ojo derecho (rojo)
        for start, end in right_regions:
            if end > start and (end - start) > 0.001:  # Validar región
                region = pg.LinearRegionItem(
                    values=[start, end],
                    brush=pg.mkBrush(255, 0, 0, 50),
                    movable=False
                )
                plot.addItem(region)
    
    def _detect_blink_regions_from_data(self, visible_data: Dict) -> Tuple[List, List]:
        """
        Detecta regiones de parpadeo desde los datos visibles.
        
        Args:
            visible_data: Datos visibles
            
        Returns:
            Tupla con (regiones_izquierdo, regiones_derecho)
        """
        left_regions = []
        right_regions = []
        
        if 'left_eye_states' in visible_data and 'timestamps' in visible_data:
            left_regions = self._find_blink_regions(
                visible_data['timestamps'],
                visible_data['left_eye_states']
            )
        
        if 'right_eye_states' in visible_data and 'timestamps' in visible_data:
            right_regions = self._find_blink_regions(
                visible_data['timestamps'],
                visible_data['right_eye_states']
            )
        
        return left_regions, right_regions
    
    def _find_blink_regions(self, timestamps: np.ndarray, eye_states: np.ndarray) -> List[Tuple]:
        """
        Encuentra regiones de parpadeo en los datos.
        
        Args:
            timestamps: Array de timestamps
            eye_states: Array de estados del ojo (True = visible, False = parpadeo)
            
        Returns:
            Lista de tuplas (inicio, fin) de regiones de parpadeo
        """
        regions = []
        in_blink = False
        blink_start = None
        
        for timestamp, is_visible in zip(timestamps, eye_states):
            if not is_visible and not in_blink:
                # Inicio de parpadeo
                in_blink = True
                blink_start = timestamp
            elif is_visible and in_blink:
                # Fin de parpadeo
                in_blink = False
                if blink_start is not None:
                    regions.append((blink_start, timestamp))
                blink_start = None
        
        # Cerrar parpadeo si termina en el límite
        if in_blink and blink_start is not None and len(timestamps) > 0:
            regions.append((blink_start, timestamps[-1]))
        
        return regions
    
    def _apply_auto_scroll(self, plots: List, timestamps: np.ndarray):
        """
        Aplica auto-scroll optimizado a los gráficos.
        
        Args:
            plots: Lista de gráficos
            timestamps: Array de timestamps visibles
        """
        if not self.auto_scroll or len(timestamps) == 0:
            return
        
        current_time = timestamps[-1]
        
        # Calcular ventana de visualización
        if current_time < self.window_size * 2/3:
            window_start = 0
            window_end = self.window_size
        else:
            window_start = current_time - (self.window_size * 2/3)
            window_end = window_start + self.window_size
        
        # Verificar si el rango cambió significativamente
        current_range = (window_start, window_end)
        if (self.last_visible_range is not None and 
            abs(current_range[0] - self.last_visible_range[0]) < 0.1 and
            abs(current_range[1] - self.last_visible_range[1]) < 0.1):
            return  # No cambio significativo
        
        # Aplicar nuevo rango
        self._updating_range = True
        try:
            for plot in plots:
                plot.setXRange(window_start, window_end, padding=0)
            self.last_visible_range = current_range
        finally:
            self._updating_range = False
    
    def _calculate_data_hash(self, data: Dict) -> int:
        """
        Calcula un hash simple de los datos para detectar cambios.
        
        Args:
            data: Diccionario de datos
            
        Returns:
            Hash de los datos
        """
        try:
            # Hash basado en el último timestamp y cantidad de datos
            timestamps = data.get('timestamps', [])
            if len(timestamps) > 0:
                last_time = timestamps[-1] if hasattr(timestamps, '__getitem__') else timestamps
                return hash((len(timestamps), float(last_time)))
            return 0
        except:
            return 0
    
    def _update_cache(self, data: Dict, visible_data: Dict, current_time: float):
        """
        Actualiza el cache de renderizado.
        
        Args:
            data: Datos completos
            visible_data: Datos visibles
            current_time: Tiempo actual
        """
        if self.optimization_config['cache_enabled']:
            self.last_data_hash = self._calculate_data_hash(data)
            self._last_cache_time = current_time
            
            # Guardar snapshot de datos visibles para cache
            self._render_cache = {
                'visible_data': visible_data.copy(),
                'timestamp': current_time
            }
    
    def _update_stats(self, start_time: float):
        """
        Actualiza las estadísticas de rendering.
        
        Args:
            start_time: Tiempo de inicio del rendering
        """
        render_time = time.time() - start_time
        self.render_stats['last_render_time'] = render_time
        self.render_stats['total_renders'] += 1
        
        # Calcular promedio móvil
        alpha = 0.1
        self.render_stats['avg_render_time'] = (
            alpha * render_time + 
            (1 - alpha) * self.render_stats['avg_render_time']
        )
    
    def _empty_visible_data(self) -> Dict:
        """Retorna un diccionario con datos vacíos."""
        return {
            'timestamps': np.array([]),
            'left_eye_x': np.array([]),
            'left_eye_y': np.array([]),
            'right_eye_x': np.array([]),
            'right_eye_y': np.array([]),
            'imu_x': np.array([]),
            'imu_y': np.array([]),
            'left_eye_states': np.array([]),
            'right_eye_states': np.array([])
        }
    
    def set_window_size(self, size: float):
        """
        Establece el tamaño de la ventana visible.
        
        Args:
            size: Tamaño en segundos
        """
        self.window_size = max(1.0, size)
        self._invalidate_cache()
    
    def set_auto_scroll(self, enabled: bool, force: bool = False):
        """
        Activa o desactiva el auto-scroll.
        
        Args:
            enabled: True para activar
            force: True para forzar el cambio
        """
        if force or not self._updating_range:
            self.auto_scroll = enabled
    
    def set_max_visible_points(self, max_points: int):
        """
        Establece el máximo número de puntos visibles.
        
        Args:
            max_points: Máximo número de puntos
        """
        self.max_visible_points = max(100, min(max_points, 10000))
        self._invalidate_cache()
    
    def enable_performance_mode(self, enabled: bool):
        """
        Activa o desactiva el modo de alto rendimiento.
        
        Args:
            enabled: True para activar modo performance
        """
        self.optimization_config['performance_mode'] = enabled
        
        if enabled:
            # Configuración para máximo rendimiento
            self.optimization_config['adaptive_downsampling'] = True
            self.optimization_config['cache_enabled'] = True
            self.optimization_config['blink_region_limit'] = 20
            self.max_visible_points = 1000
            self._cache_validity_time = 0.2  # Cache más duradero
            print("VisualManager: Modo performance activado")
        else:
            # Configuración normal
            self.optimization_config['adaptive_downsampling'] = True
            self.optimization_config['cache_enabled'] = True
            self.optimization_config['blink_region_limit'] = 50
            self.max_visible_points = 2000
            self._cache_validity_time = 0.1
            print("VisualManager: Modo normal activado")
        
        self._invalidate_cache()
    
    def _invalidate_cache(self):
        """Invalida el cache forzando una actualización."""
        self._render_cache.clear()
        self.last_data_hash = None
        self._last_cache_time = 0
    
    def get_performance_stats(self) -> Dict:
        """
        Obtiene estadísticas de performance del visual manager.
        
        Returns:
            Diccionario con estadísticas
        """
        total_requests = self.render_stats['cache_hits'] + self.render_stats['cache_misses']
        cache_hit_rate = (
            self.render_stats['cache_hits'] / max(1, total_requests) * 100
        )
        
        return {
            'total_renders': self.render_stats['total_renders'],
            'avg_render_time_ms': self.render_stats['avg_render_time'] * 1000,
            'last_render_time_ms': self.render_stats['last_render_time'] * 1000,
            'cache_hit_rate_percent': cache_hit_rate,
            'max_visible_points': self.max_visible_points,
            'window_size_seconds': self.window_size,
            'auto_scroll_enabled': self.auto_scroll,
            'performance_mode': self.optimization_config['performance_mode'],
            'cache_enabled': self.optimization_config['cache_enabled']
        }
    
    def optimize_for_data_size(self, data_size: int):
        """
        Optimiza automáticamente basado en el tamaño de datos.
        
        Args:
            data_size: Tamaño actual de los datos
        """
        if data_size > 50000:
            # Datos muy grandes
            self.enable_performance_mode(True)
            self.set_max_visible_points(800)
            print(f"VisualManager: Auto-optimización para {data_size} puntos (modo ultra-performance)")
            
        elif data_size > 20000:
            # Datos grandes
            self.enable_performance_mode(True)
            self.set_max_visible_points(1200)
            print(f"VisualManager: Auto-optimización para {data_size} puntos (modo performance)")
            
        elif data_size > 10000:
            # Datos moderados
            self.enable_performance_mode(False)
            self.set_max_visible_points(1500)
            
        else:
            # Datos pequeños - configuración normal
            self.enable_performance_mode(False)
            self.set_max_visible_points(2000)
    
    def is_updating_range(self) -> bool:
        """Retorna True si está actualizando el rango."""
        return self._updating_range
    
    def force_update(self):
        """Fuerza una actualización en el próximo render."""
        self._invalidate_cache()
    
    def get_optimization_config(self) -> Dict:
        """Retorna la configuración actual de optimización."""
        return self.optimization_config.copy()