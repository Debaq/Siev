import { useState, useEffect, useRef } from 'react'

export const SmartDateInput = ({ value, onChange }: { value: string, onChange: (val: string) => void }) => {
  // Split YYYY-MM-DD
  const [y, m, d] = value ? value.split('-') : ['', '', '']
  
  const [day, setDay] = useState(d || '')
  const [month, setMonth] = useState(m || '')
  const [year, setYear] = useState(y || '')

  const dayRef = useRef<HTMLInputElement>(null)
  const monthRef = useRef<HTMLInputElement>(null)
  const yearRef = useRef<HTMLInputElement>(null)

  // Sync internal state if external value changes (e.g. edit mode loaded)
  useEffect(() => {
    const [ny, nm, nd] = value ? value.split('-') : ['', '', '']
    setDay(nd || '')
    setMonth(nm || '')
    setYear(ny || '')
  }, [value])

  const notifyChange = (d: string, m: string, y: string) => {
    if (d && m && y && y.length === 4) {
      onChange(`${y}-${m}-${d}`)
    } else {
        onChange('') // Clear if incomplete to avoid invalid dates
    }
  }

  const handleDayChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let val = e.target.value.replace(/\D/g, '').slice(0, 2)
    
    // Auto-pad single digit if > 3 (e.g. 4 -> 04)
    if (val.length === 1 && parseInt(val) > 3) {
      val = '0' + val
      setDay(val)
      notifyChange(val, month, year)
      monthRef.current?.focus()
    } else {
      setDay(val)
      notifyChange(val, month, year)
      if (val.length === 2) monthRef.current?.focus()
    }
  }

  const handleMonthChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let val = e.target.value.replace(/\D/g, '').slice(0, 2)

    // Auto-pad single digit if > 1 (e.g. 2 -> 02)
    if (val.length === 1 && parseInt(val) > 1) {
      val = '0' + val
      setMonth(val)
      notifyChange(day, val, year)
      yearRef.current?.focus()
    } else {
      setMonth(val)
      notifyChange(day, val, year)
      if (val.length === 2) yearRef.current?.focus()
    }
  }

  // Handle Backspace to move backwards
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, field: 'day' | 'month' | 'year') => {
    if (e.key === 'Backspace' && (e.currentTarget.value === '')) {
        if (field === 'month') dayRef.current?.focus()
        if (field === 'year') monthRef.current?.focus()
    }
  }

  const handleYearChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/\D/g, '').slice(0, 4)
    setYear(val)
    notifyChange(day, month, val)
  }

  const handleYearBlur = () => {
    if (year.length === 2) {
      const currentYear = new Date().getFullYear()
      const currentCentury = Math.floor(currentYear / 100) * 100
      const shortYear = parseInt(year)
      const currentShort = currentYear % 100

      // Logic: 86 -> 1986 (if current is 26)
      // Logic: 06 -> 2006
      let fullYear = 0
      if (shortYear > currentShort) {
        fullYear = (currentCentury - 100) + shortYear
      } else {
        fullYear = currentCentury + shortYear
      }
      
      const strYear = fullYear.toString()
      setYear(strYear)
      notifyChange(day, month, strYear)
    }
  }

  return (
    <div className="input flex items-center gap-1 p-0 overflow-hidden bg-dark-950 focus-within:border-siev-500 transition-colors">
      <input
        ref={dayRef}
        value={day}
        onChange={handleDayChange}
        onKeyDown={(e) => handleKeyDown(e, 'day')}
        placeholder="DD"
        className="bg-transparent w-8 text-center outline-none placeholder-dark-600"
      />
      <span className="text-dark-500">/</span>
      <input
        ref={monthRef}
        value={month}
        onChange={handleMonthChange}
        onKeyDown={(e) => handleKeyDown(e, 'month')}
        placeholder="MM"
        className="bg-transparent w-8 text-center outline-none placeholder-dark-600"
      />
      <span className="text-dark-500">/</span>
      <input
        ref={yearRef}
        value={year}
        onChange={handleYearChange}
        onBlur={handleYearBlur}
        onKeyDown={(e) => handleKeyDown(e, 'year')}
        placeholder="AAAA"
        className="bg-transparent flex-1 outline-none placeholder-dark-600"
      />
    </div>
  )
}
