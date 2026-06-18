// components/Wordmark.tsx — FUSION lockup: the green "F" logo glyph followed by
// lowercase "usion" as text on one line. The "i" is rendered dotless (U+0131) so
// we can place a brand-green tittle above it; the remaining letters inherit the
// theme text colour (white in dark, near-black in light).
import React from 'react'
import Logo from './Logo'

interface WordmarkProps {
  /** Wrapper classes — use to size the text (e.g. text-[15px]). */
  className?: string
  /** Logo glyph classes — controls the F size. */
  logoClassName?: string
}

export default function Wordmark({
  className = 'text-[15px]',
  logoClassName = 'w-7 h-7',
}: WordmarkProps) {
  return (
    <span
      className={`inline-flex items-center font-bold tracking-tight leading-none select-none ${className}`}
      aria-label="FUSION"
      role="img"
    >
      <Logo className={`${logoClassName} text-accent shrink-0`} title="FUSION" />
      <span className="text-text-primary lowercase -ml-[0.12em]" aria-hidden="true">
        us
        <span className="relative inline-block">
          {'ı'}
          {/* brand-green tittle above the dotless i */}
          <span className="absolute left-1/2 -translate-x-1/2 bottom-[0.74em] w-[0.16em] h-[0.16em] rounded-full bg-accent" />
        </span>
        on
      </span>
    </span>
  )
}
