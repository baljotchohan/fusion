// components/BandLogoFull.tsx
// Pixel-accurate BAND AI brand lockup — auto-traced from official band_logo.png.
// All coordinates are pre-computed for viewBox "0 0 820 200":
//   • Icon (robot face) lives in 0-200 x-space
//   • "BAND" text lives in 220-820 x-space (220px offset from icon)
// Letters B, A, D have inner counter holes: outer + inner sub-paths merged into
// one <path> d string with fillRule="evenodd" to punch the holes correctly.
import React from 'react'

interface BandLogoFullProps {
  className?: string
}

export default function BandLogoFull({ className = 'h-7' }: BandLogoFullProps) {
  return (
    <svg
      viewBox="0 0 820 200"
      className={`w-auto ${className}`}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="BAND AI"
    >
      <defs>
        <radialGradient id="bgFull" cx="35%" cy="30%" r="70%">
          <stop offset="0%" stopColor="#4ADE80" />
          <stop offset="55%" stopColor="#22C55E" />
          <stop offset="100%" stopColor="#166534" />
        </radialGradient>
      </defs>

      {/* ── Robot face icon (0-200 x-space, 200×200) ── */}

      {/* Ground shadow oval (green) */}
      <path
        fill="url(#bgFull)"
        opacity="0.6"
        d="M 87.64 166.32 L 88.73 168.75 L 92.73 169.79 L 124.73 172.22 L 168.73 171.18
           L 179.64 169.79 L 184.73 167.71 L 184.36 165.97 L 180.36 164.58 L 161.09 162.50
           L 154.91 162.50 L 149.09 164.24 L 140.00 165.28 L 128.00 164.93 L 117.09 162.50
           L 110.91 162.50 L 93.82 164.24 Z"
      />

      {/* Outer green ring (solid) */}
      <path
        fill="url(#bgFull)"
        d="M 125.45 42.71 L 104.73 49.31 L 92.73 57.29 L 83.64 66.32 L 73.09 87.50
           L 72.36 112.15 L 81.45 133.68 L 99.64 150.69 L 112.36 156.94 L 124.36 160.07
           L 147.64 160.42 L 168.73 153.12 L 178.91 146.53 L 189.45 135.76 L 199.64 114.24
           L 199.64 88.89 L 192.00 70.83 L 173.09 52.43 L 150.91 43.40 Z"
      />

      {/* Dark face circle (the main face interior) */}
      <path
        fill="#071510"
        d="M 137.82 53.47 L 127.27 56.25 L 118.91 60.42 L 105.45 72.92 L 101.09 80.21
           L 97.82 89.93 L 97.45 106.60 L 104.00 123.26 L 109.82 130.56 L 117.45 136.81
           L 125.82 141.32 L 134.91 144.10 L 151.64 144.79 L 160.73 142.71 L 171.27 137.85
           L 185.09 125.00 L 192.36 108.68 L 192.73 91.67 L 190.18 82.64 L 185.82 74.31
           L 172.00 60.76 L 156.36 54.17 Z"
      />

      {/* Right cyan eye */}
      <path
        fill="#22D3EE"
        d="M 171.27 83.33 L 168.73 85.07 L 166.91 87.50 L 165.82 89.93 L 164.73 93.75
           L 164.73 95.49 L 164.36 95.83 L 164.36 102.78 L 164.73 103.12 L 164.73 105.21
           L 166.18 109.72 L 168.73 113.54 L 171.27 115.28 L 174.55 115.28 L 177.45 113.19
           L 180.00 109.03 L 181.09 105.21 L 181.09 103.82 L 181.45 103.47 L 181.45 95.49
           L 181.09 95.14 L 181.09 93.40 L 180.73 93.06 L 180.36 90.62 L 177.82 85.76
           L 176.00 84.03 L 174.55 83.33 Z"
      />

      {/* Left cyan eye */}
      <path
        fill="#22D3EE"
        d="M 129.45 81.25 L 127.27 82.29 L 124.36 85.07 L 122.18 88.89 L 120.36 95.83
           L 120.36 103.12 L 121.82 109.03 L 124.73 114.24 L 127.64 116.67 L 129.09 117.36
           L 132.00 117.71 L 135.64 116.32 L 138.18 113.89 L 140.36 110.07 L 142.18 103.47
           L 142.18 95.83 L 140.36 88.89 L 138.55 85.42 L 137.09 83.68 L 134.18 81.60 Z"
      />

      {/* ── "BAND" text (220-820 x-space) ── */}
      {/* All coordinates already offset by +220 from the 600×200 text trace space */}
      <g className="fill-current text-neutral-900 dark:text-white">

        {/* D outer — solid (no inner hole needed, counter filled by dark bg overlap) */}
        {/* D outer + D inner counter: combined with evenodd */}
        <path
          fillRule="evenodd"
          d="M 603.51 60.42 L 603.51 148.26 L 662.77 148.26 L 677.23 145.83 L 691.70 139.93
             L 698.69 134.72 L 705.69 126.04 L 710.82 108.68 L 708.02 87.85 L 698.69 73.96
             L 687.03 66.32 L 669.77 61.46 Z
             M 628.71 74.65 L 662.77 75.35 L 673.03 78.47 L 678.63 83.33 L 681.43 89.24
             L 682.83 97.57 L 682.36 115.97 L 679.10 125.00 L 670.23 131.60 L 656.70 134.03
             L 628.24 133.68 Z"
        />

        {/* A outer + A inner triangle: combined with evenodd */}
        <path
          fillRule="evenodd"
          d="M 419.22 60.42 L 372.10 155.90 L 402.43 148.96 L 412.22 129.86 L 456.08 129.86
             L 465.88 148.96 L 495.74 155.90 L 449.08 60.42 Z
             M 431.35 80.56 L 436.49 80.56 L 437.42 81.25 L 440.68 93.06 L 450.02 114.24
             L 449.55 115.28 L 418.29 115.28 L 417.82 114.93 L 425.75 96.88 L 429.49 86.11
             L 430.42 81.60 Z"
        />

        {/* B outer + B upper counter + B lower counter: all three in one evenodd path */}
        <path
          fillRule="evenodd"
          d="M 286.72 60.42 L 286.72 148.61 L 348.77 148.61 L 367.90 145.83 L 382.83 116.67
             L 379.56 110.76 L 365.57 103.12 L 366.03 100.35 L 376.30 93.75 L 380.03 87.15
             L 380.03 76.04 L 375.37 68.40 L 365.10 62.85 L 354.37 60.76 Z
             M 311.45 74.65 L 311.91 74.31 L 344.11 74.31 L 349.24 75.69 L 352.97 78.82
             L 354.37 82.64 L 354.37 88.19 L 352.97 92.01 L 349.24 95.14 L 345.51 96.18
             L 311.91 96.18 L 311.45 95.83 Z
             M 311.45 110.42 L 311.91 110.07 L 345.04 110.07 L 348.30 110.42 L 351.57 111.46
             L 355.30 114.24 L 357.64 119.10 L 357.64 125.35 L 355.77 129.86 L 352.50 132.64
             L 345.97 134.38 L 311.91 134.38 L 311.45 134.03 Z"
        />

        {/* N — no inner hole */}
        <path
          d="M 589.98 52.43 L 566.66 52.78 L 568.52 121.53 L 561.52 121.18 L 517.20 60.42
             L 485.94 60.42 L 485.47 115.62 L 502.74 148.61 L 509.27 148.26 L 507.87 87.50
             L 514.87 87.85 L 559.19 148.26 L 589.98 148.61 Z"
        />
      </g>
    </svg>
  )
}
