import { Trash2 } from 'lucide-react'
import type { Ear, VocalData, ThresholdMeasurement, UMDEntry } from '../../../types/audiometry'

interface SpeechDataEntryProps {
  vocal: VocalData
  onUpdateSDT: (ear: Ear, field: 'intensity' | 'mkg', value: number | undefined) => void
  onUpdateSRT: (ear: Ear, field: 'intensity' | 'mkg', value: number | undefined) => void
  onUpdateUMD: (ear: Ear, index: number, field: keyof UMDEntry, value: number | undefined) => void
  onRemoveUMD: (ear: Ear, index: number) => void
}

function numVal(v: number | undefined): string {
  return v !== undefined ? String(v) : ''
}

function parseNum(s: string): number | undefined {
  return s === '' ? undefined : Number(s)
}

function MkgToggle({
  active,
  onToggle,
}: {
  active: boolean
  onToggle: () => void
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`w-5 h-5 rounded text-[9px] font-bold shrink-0 transition-colors ${
        active
          ? 'bg-amber-500/80 text-white'
          : 'bg-dark-800 text-dark-500 hover:bg-dark-700'
      }`}
      title="Masking (MKG)"
    >
      M
    </button>
  )
}

function ThresholdRow({
  label,
  od,
  oi,
  onChangeOD,
  onChangeOI,
}: {
  label: string
  od: ThresholdMeasurement | undefined
  oi: ThresholdMeasurement | undefined
  onChangeOD: (field: 'intensity' | 'mkg', value: number | undefined) => void
  onChangeOI: (field: 'intensity' | 'mkg', value: number | undefined) => void
}) {
  const hasMkgOD = od?.mkg !== undefined
  const hasMkgOI = oi?.mkg !== undefined

  return (
    <tr className="border-b border-dark-700/50">
      <td className="py-1 px-2 text-[10px] font-semibold text-dark-300 whitespace-nowrap">
        {label}
      </td>
      {/* OD */}
      <td className="py-1 px-1">
        <div className="flex items-center gap-1">
          <input
            type="number"
            value={numVal(od?.intensity)}
            onChange={e => onChangeOD('intensity', parseNum(e.target.value))}
            className="w-14 bg-dark-900 border border-dark-700 rounded px-1.5 py-0.5 text-[10px] text-white"
            placeholder="dB"
            step={5}
          />
          <MkgToggle
            active={hasMkgOD}
            onToggle={() => onChangeOD('mkg', hasMkgOD ? undefined : 0)}
          />
          {hasMkgOD && (
            <input
              type="number"
              value={numVal(od?.mkg)}
              onChange={e => onChangeOD('mkg', parseNum(e.target.value))}
              className="w-12 bg-dark-900 border border-amber-600/40 rounded px-1 py-0.5 text-[10px] text-amber-300"
              placeholder="mkg"
              step={5}
            />
          )}
        </div>
      </td>
      {/* OI */}
      <td className="py-1 px-1">
        <div className="flex items-center gap-1">
          <input
            type="number"
            value={numVal(oi?.intensity)}
            onChange={e => onChangeOI('intensity', parseNum(e.target.value))}
            className="w-14 bg-dark-900 border border-dark-700 rounded px-1.5 py-0.5 text-[10px] text-white"
            placeholder="dB"
            step={5}
          />
          <MkgToggle
            active={hasMkgOI}
            onToggle={() => onChangeOI('mkg', hasMkgOI ? undefined : 0)}
          />
          {hasMkgOI && (
            <input
              type="number"
              value={numVal(oi?.mkg)}
              onChange={e => onChangeOI('mkg', parseNum(e.target.value))}
              className="w-12 bg-dark-900 border border-amber-600/40 rounded px-1 py-0.5 text-[10px] text-amber-300"
              placeholder="mkg"
              step={5}
            />
          )}
        </div>
      </td>
    </tr>
  )
}

function UMDRow({
  od,
  oi,
  onChangeOD,
  onChangeOI,
  onRemoveOD,
  onRemoveOI,
  showLabel,
}: {
  od: UMDEntry | undefined
  oi: UMDEntry | undefined
  onChangeOD: (field: keyof UMDEntry, value: number | undefined) => void
  onChangeOI: (field: keyof UMDEntry, value: number | undefined) => void
  onRemoveOD: (() => void) | null
  onRemoveOI: (() => void) | null
  showLabel: boolean
}) {
  const odHasData = od && (od.intensity !== undefined || od.percentage !== undefined)
  const oiHasData = oi && (oi.intensity !== undefined || oi.percentage !== undefined)
  const hasMkgOD = od?.mkg !== undefined
  const hasMkgOI = oi?.mkg !== undefined

  return (
    <tr className="border-b border-dark-700/30">
      <td className="py-1 px-2 text-[10px] font-semibold text-dark-300 whitespace-nowrap">
        {showLabel ? 'UMD' : ''}
      </td>
      {/* OD */}
      <td className="py-1 px-1">
        <div className="flex items-center gap-1">
          <input
            type="number"
            value={numVal(od?.intensity)}
            onChange={e => onChangeOD('intensity', parseNum(e.target.value))}
            className="w-14 bg-dark-900 border border-dark-700 rounded px-1.5 py-0.5 text-[10px] text-white"
            placeholder="dB"
            step={5}
          />
          <input
            type="number"
            value={numVal(od?.percentage)}
            onChange={e => onChangeOD('percentage', parseNum(e.target.value))}
            className="w-12 bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[10px] text-white"
            placeholder="%"
            min={0}
            max={100}
          />
          <MkgToggle
            active={hasMkgOD}
            onToggle={() => onChangeOD('mkg', hasMkgOD ? undefined : 0)}
          />
          {hasMkgOD && (
            <input
              type="number"
              value={numVal(od?.mkg)}
              onChange={e => onChangeOD('mkg', parseNum(e.target.value))}
              className="w-10 bg-dark-900 border border-amber-600/40 rounded px-1 py-0.5 text-[10px] text-amber-300"
              placeholder="mkg"
              step={5}
            />
          )}
          {odHasData && onRemoveOD && (
            <button
              onClick={onRemoveOD}
              className="text-dark-600 hover:text-red-400 transition-colors shrink-0"
              title="Eliminar"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          )}
        </div>
      </td>
      {/* OI */}
      <td className="py-1 px-1">
        <div className="flex items-center gap-1">
          <input
            type="number"
            value={numVal(oi?.intensity)}
            onChange={e => onChangeOI('intensity', parseNum(e.target.value))}
            className="w-14 bg-dark-900 border border-dark-700 rounded px-1.5 py-0.5 text-[10px] text-white"
            placeholder="dB"
            step={5}
          />
          <input
            type="number"
            value={numVal(oi?.percentage)}
            onChange={e => onChangeOI('percentage', parseNum(e.target.value))}
            className="w-12 bg-dark-900 border border-dark-700 rounded px-1 py-0.5 text-[10px] text-white"
            placeholder="%"
            min={0}
            max={100}
          />
          <MkgToggle
            active={hasMkgOI}
            onToggle={() => onChangeOI('mkg', hasMkgOI ? undefined : 0)}
          />
          {hasMkgOI && (
            <input
              type="number"
              value={numVal(oi?.mkg)}
              onChange={e => onChangeOI('mkg', parseNum(e.target.value))}
              className="w-10 bg-dark-900 border border-amber-600/40 rounded px-1 py-0.5 text-[10px] text-amber-300"
              placeholder="mkg"
              step={5}
            />
          )}
          {oiHasData && onRemoveOI && (
            <button
              onClick={onRemoveOI}
              className="text-dark-600 hover:text-blue-400 transition-colors shrink-0"
              title="Eliminar"
            >
              <Trash2 className="w-3 h-3" />
            </button>
          )}
        </div>
      </td>
    </tr>
  )
}

export default function SpeechDataEntry({
  vocal,
  onUpdateSDT,
  onUpdateSRT,
  onUpdateUMD,
  onRemoveUMD,
}: SpeechDataEntryProps) {
  const umdRows = Math.max(vocal.umd_od.length, vocal.umd_oi.length)

  return (
    <div className="h-full overflow-y-auto custom-scrollbar p-3">
      <table className="w-full border-collapse">
        <thead>
          <tr className="border-b border-dark-600">
            <th className="text-[10px] text-dark-400 font-medium text-left px-2 py-1.5 w-14">
              Medida
            </th>
            <th className="text-[10px] font-bold text-red-400 text-left px-1 py-1.5">
              OD
            </th>
            <th className="text-[10px] font-bold text-blue-400 text-left px-1 py-1.5">
              OI
            </th>
          </tr>
        </thead>
        <tbody>
          <ThresholdRow
            label="SDT"
            od={vocal.sdt_od}
            oi={vocal.sdt_oi}
            onChangeOD={(f, v) => onUpdateSDT('od', f, v)}
            onChangeOI={(f, v) => onUpdateSDT('oi', f, v)}
          />
          <ThresholdRow
            label="SRT"
            od={vocal.srt_od}
            oi={vocal.srt_oi}
            onChangeOD={(f, v) => onUpdateSRT('od', f, v)}
            onChangeOI={(f, v) => onUpdateSRT('oi', f, v)}
          />
          {Array.from({ length: umdRows }, (_, i) => (
            <UMDRow
              key={i}
              od={vocal.umd_od[i]}
              oi={vocal.umd_oi[i]}
              onChangeOD={(f, v) => onUpdateUMD('od', i, f, v)}
              onChangeOI={(f, v) => onUpdateUMD('oi', i, f, v)}
              onRemoveOD={
                vocal.umd_od.length > 1 && i < vocal.umd_od.length
                  ? () => onRemoveUMD('od', i)
                  : null
              }
              onRemoveOI={
                vocal.umd_oi.length > 1 && i < vocal.umd_oi.length
                  ? () => onRemoveUMD('oi', i)
                  : null
              }
              showLabel={i === 0}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}
