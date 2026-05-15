import { useEffect, useMemo, useState } from 'react';
import * as api from '../api';

function startOfMonth(y, m) { return new Date(y, m - 1, 1); }
function daysInMonth(y, m) { return new Date(y, m, 0).getDate(); }
function pad(n) { return String(n).padStart(2, '0'); }

export default function DailyCalendarModal({ open, onClose, onOpenDailyNote }) {
  const today = useMemo(() => new Date(), []);
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [haveDates, setHaveDates] = useState(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.getDailyCalendar(year, month)
      .then((dates) => { if (!cancelled) setHaveDates(new Set(dates)); })
      .catch((e) => { if (!cancelled) setError(e.message || 'Failed to load calendar'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [open, year, month]);

  if (!open) return null;

  const total = daysInMonth(year, month);
  const firstDow = (startOfMonth(year, month).getDay() + 6) % 7; // Monday-first
  const cells = [];
  for (let i = 0; i < firstDow; i++) cells.push(null);
  for (let d = 1; d <= total; d++) cells.push(d);
  while (cells.length % 7) cells.push(null);

  function shift(months) {
    let m = month + months;
    let y = year;
    while (m < 1) { m += 12; y -= 1; }
    while (m > 12) { m -= 12; y += 1; }
    setYear(y);
    setMonth(m);
  }

  const monthName = startOfMonth(year, month).toLocaleString(undefined, { month: 'long', year: 'numeric' });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose && onClose(); }}
    >
      <div className="w-full max-w-md flex flex-col bg-surface-1 border border-line-1 rounded-2xl shadow-glow-cobalt overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-line-1">
          <div className="flex items-center gap-2">
            <button onClick={() => shift(-1)} className="text-ink-3 hover:text-ink-1" aria-label="Previous month">‹</button>
            <div className="text-base font-display text-ink-1 tabular-nums">📅 {monthName}</div>
            <button onClick={() => shift(1)} className="text-ink-3 hover:text-ink-1" aria-label="Next month">›</button>
          </div>
          <button onClick={onClose} className="text-ink-3 hover:text-ink-1" aria-label="Close">✕</button>
        </div>
        <div className="p-4">
          {error && <div className="text-sm text-semantic-danger mb-2">{error}</div>}
          {loading && <div className="text-xs text-ink-3 mb-2">Loading…</div>}
          <div className="grid grid-cols-7 gap-1 text-center text-[10px] uppercase tracking-wider text-ink-4 mb-1">
            {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => <div key={d}>{d}</div>)}
          </div>
          <div className="grid grid-cols-7 gap-1">
            {cells.map((d, i) => {
              if (d == null) return <div key={i} />;
              const iso = `${year}-${pad(month)}-${pad(d)}`;
              const hasNote = haveDates.has(iso);
              const isToday = today.getFullYear() === year && today.getMonth() + 1 === month && today.getDate() === d;
              return (
                <button
                  key={i}
                  onClick={() => onOpenDailyNote && onOpenDailyNote(iso)}
                  className={`relative aspect-square rounded text-sm flex items-center justify-center
                    ${isToday ? 'ring-1 ring-brand-orange' : ''}
                    ${hasNote ? 'bg-brand-cobalt/30 text-ink-1' : 'bg-surface-2 hover:bg-surface-3 text-ink-2'}`}
                  title={hasNote ? `Open ${iso}` : `Create ${iso}`}
                >
                  {d}
                  {hasNote && <span className="absolute bottom-0.5 right-1 w-1.5 h-1.5 rounded-full bg-brand-cobalt-300" />}
                </button>
              );
            })}
          </div>
        </div>
        <div className="px-4 py-2 border-t border-line-1 text-xs text-ink-4">
          Click a day to open (or create) its daily note. Cobalt cells already have one.
        </div>
      </div>
    </div>
  );
}
