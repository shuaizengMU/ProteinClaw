interface Props {
  size?: number;
  color?: string;
}

export function ClaudeLogo({ size = 20, color = "#da7756" }: Props) {
  const cx = size / 2;
  const cy = size / 2;
  const r1 = size * 0.06;
  const r2 = size * 0.42;
  const spokes = 8;
  const sw = size * 0.11;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} fill="none">
      {Array.from({ length: spokes }).map((_, i) => {
        const angle = (i * Math.PI * 2) / spokes - Math.PI / 2;
        return (
          <line
            key={i}
            x1={cx + r1 * Math.cos(angle)}
            y1={cy + r1 * Math.sin(angle)}
            x2={cx + r2 * Math.cos(angle)}
            y2={cy + r2 * Math.sin(angle)}
            stroke={color}
            strokeWidth={sw}
            strokeLinecap="round"
          />
        );
      })}
    </svg>
  );
}
