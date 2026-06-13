// components/Logo.tsx — FUSION letter "f" logo.
// Traced directly from the official logofusion.png to ensure perfect vector accuracy.
// Uses currentColor to scale and style with Tailwind text colors (e.g. text-accent).
import React from 'react'

interface LogoProps {
  className?: string
  title?: string
}

export default function Logo({ className = 'w-6 h-6 text-accent', title = 'FUSION' }: LogoProps) {
  return (
    <svg
      viewBox="0 0 64 64"
      className={className}
      role="img"
      aria-label={title}
      fill="currentColor"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* stem */}
      <path
        d="M 45.61 25.8 L 34.56 25.8 L 32.0 28.36 L 27.15 31.46 L 19.61 35.1 L 14.76 36.98 L 12.06 37.66 L 11.66 38.06 L 11.79 45.61 L 11.12 51.67 L 9.37 58.0 L 10.98 57.6 L 14.62 55.44 L 19.74 50.32 L 22.17 46.68 L 24.46 41.83 L 26.34 35.77 L 27.69 36.04 L 32.0 35.91 L 36.72 34.02 L 40.08 31.73 L 44.66 27.55 Z"
        opacity="0.85"
      />
      {/* crossbar */}
      <path
        d="M 23.92 22.44 L 15.03 22.44 L 13.54 23.38 L 12.47 24.46 L 12.47 24.59 L 12.06 24.99 L 11.93 25.94 L 11.79 26.07 L 11.79 29.31 L 11.66 29.44 L 11.79 29.58 L 11.79 29.98 L 11.66 30.11 L 11.66 34.83 L 11.79 34.96 L 11.79 35.5 L 12.47 35.5 L 14.89 34.02 L 15.56 33.35 L 15.7 33.35 L 17.72 31.6 L 17.85 31.6 L 17.99 31.33 L 18.39 31.06 L 18.66 30.65 L 18.8 30.65 L 19.2 29.98 L 19.47 29.84 L 20.95 28.23 L 21.09 27.82 L 22.03 26.61 L 22.03 26.34 L 22.97 25.13 L 23.65 23.65 L 23.65 23.38 L 23.92 22.97 Z"
        opacity="0.75"
      />
      {/* top_hook */}
      <path
        d="M 57.33 6.4 L 56.65 6.0 L 51.94 7.08 L 45.74 7.48 L 20.55 7.35 L 17.18 8.02 L 13.14 10.45 L 9.1 15.3 L 9.23 15.56 L 6.67 21.22 L 6.81 22.44 L 7.21 22.44 L 8.96 20.68 L 10.85 19.61 L 15.3 18.53 L 43.59 18.53 L 47.22 17.72 L 50.73 15.97 L 53.42 13.41 L 55.44 10.45 Z"
        opacity="0.9"
      />
    </svg>
  )
}
