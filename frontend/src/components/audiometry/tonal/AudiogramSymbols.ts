// Símbolos clínicos estándar para audiograma (ASHA)
// Color de fondo del chart para tapar la línea dentro del círculo
const CHART_BG = '#020617'

// Vía aérea OD: Círculo (O)
export const SYMBOL_AIR_OD = 'circle'
// Vía aérea OI: Cruz (X)
export const SYMBOL_AIR_OI = 'path://M4,4 L16,16 M16,4 L4,16'
// Vía ósea OD: < (abre a la izquierda)
export const SYMBOL_BONE_OD = 'path://M14,4 L6,10 L14,16'
// Vía ósea OI: > (abre a la derecha)
export const SYMBOL_BONE_OI = 'path://M6,4 L14,10 L6,16'
// Vía aérea OD enmascarada: Triángulo
export const SYMBOL_AIR_OD_MASKED = 'triangle'
// Vía aérea OI enmascarada: Cuadrado
export const SYMBOL_AIR_OI_MASKED = 'rect'
// Vía ósea OD enmascarada: [ (corchete con barra)
export const SYMBOL_BONE_OD_MASKED = 'path://M14,4 L6,10 L14,16 M6,6 L6,14'
// Vía ósea OI enmascarada: ] (corchete con barra)
export const SYMBOL_BONE_OI_MASKED = 'path://M6,4 L14,10 L6,16 M14,6 L14,14'
// LDL OD: Triángulo rectángulo a la izquierda de la intersección
// Cateto mayor horizontal (frecuencia), cateto menor vertical hacia arriba (intensidad)
export const SYMBOL_LDL_OD = 'path://M10,10 L0,10 L10,5 Z'
// LDL OI: Triángulo rectángulo a la derecha de la intersección (espejo)
export const SYMBOL_LDL_OI = 'path://M10,10 L20,10 L10,5 Z'

export interface SymbolConfig {
  symbol: string
  color: string
  size: number
  borderWidth: number
  borderColor: string
  fillColor: string
  // Offset en px [x, y] — las óseas van a los lados de la intersección
  offset: [number, number]
}

export function getSymbolConfig(
  ear: 'od' | 'oi',
  conduction: 'aerea' | 'osea' | 'ldl',
  masked: boolean
): SymbolConfig {
  const isOD = ear === 'od'
  const isAir = conduction === 'aerea'
  const isLdl = conduction === 'ldl'
  const color = isOD ? '#EF4444' : '#3B82F6'

  let symbol: string
  if (isLdl) {
    symbol = isOD ? SYMBOL_LDL_OD : SYMBOL_LDL_OI
  } else if (isAir) {
    if (masked) {
      symbol = isOD ? SYMBOL_AIR_OD_MASKED : SYMBOL_AIR_OI_MASKED
    } else {
      symbol = isOD ? SYMBOL_AIR_OD : SYMBOL_AIR_OI
    }
  } else {
    if (masked) {
      symbol = isOD ? SYMBOL_BONE_OD_MASKED : SYMBOL_BONE_OI_MASKED
    } else {
      symbol = isOD ? SYMBOL_BONE_OD : SYMBOL_BONE_OI
    }
  }

  let fillColor = 'transparent'
  if (isAir) {
    if (masked) {
      fillColor = color
    } else if (isOD) {
      fillColor = CHART_BG
    }
  }

  let offset: [number, number] = [0, 0]
  if (isLdl) {
    offset = isOD ? [-7, -3] : [7, -3]
  } else if (!isAir) {
    offset = isOD ? [-8, 0] : [8, 0]
  }

  return {
    symbol,
    color,
    size: isLdl ? 16 : isAir ? 18 : 21,
    borderWidth: isLdl ? 1.5 : 2.5,
    borderColor: color,
    fillColor,
    offset,
  }
}

export function getSeriesName(
  ear: 'od' | 'oi',
  conduction: 'aerea' | 'osea' | 'ldl',
  masked: boolean
): string {
  const earLabel = ear === 'od' ? 'OD' : 'OI'
  const condLabel = conduction === 'aerea' ? 'Aérea' : conduction === 'osea' ? 'Ósea' : 'LDL'
  const maskLabel = masked ? ' (Enm.)' : ''
  return `${earLabel} ${condLabel}${maskLabel}`
}
