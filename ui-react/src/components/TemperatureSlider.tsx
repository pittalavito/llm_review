/**
 * Range slider + live value label. The vanilla UI had three diverged copies
 * (clamp 0.1–1, 0–1 default 1, 0–1 default 0.7); min/max/step come from
 * props so each section keeps its original behavior.
 */
interface TemperatureSliderProps {
  id?: string;
  min: number;
  max: number;
  step?: number;
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
  inputClassName?: string;
  valueClassName?: string;
}

export default function TemperatureSlider({
  id, min, max, step = 0.1, value, onChange, disabled,
  inputClassName, valueClassName,
}: TemperatureSliderProps) {
  const clamp = (raw: number) => {
    if (!Number.isFinite(raw)) return max;
    return Math.min(max, Math.max(min, raw));
  };

  return (
    <>
      <input
        id={id}
        type="range"
        className={inputClassName}
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(clamp(Number.parseFloat(e.target.value)))}
      />
      <span className={valueClassName}>{clamp(value).toFixed(1)}</span>
    </>
  );
}
