import Link from 'next/link'
import { LogoMark } from '@shortgravity/ui'
import { EmailSignupForm } from '@/components/landing/EmailSignupForm'

const LIVE_ROUTES = new Set(['/signals', '/orbital', '/thesis'])

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--void-black)] flex flex-col font-mono px-6">
      {/* Main content */}
      <div className="flex-1 flex items-center justify-center py-16">
        <div className="max-w-lg w-full">
          {/* Brand */}
          <div className="text-center mb-6">
            <div className="flex items-center justify-center gap-3 mb-1">
              <LogoMark size={42} />
              <div className="text-[14px] tracking-[0.35em] text-white/90">SHORT GRAVITY</div>
            </div>
            <div className="text-[8px] text-white/25 tracking-[0.2em]">SPACE SECTOR INTELLIGENCE</div>
          </div>

          {/* Value prop */}
          <div className="text-[10px] text-white/40 leading-relaxed mb-12 text-center max-w-sm mx-auto">
            Real-time orbital tracking, patent mapping, regulatory filings, and AI-powered cross-source analysis for the space economy.
          </div>

          {/* Coverage grid */}
          <div className="mb-8">
            <div className="text-[7px] text-white/20 tracking-[0.2em] mb-3">COVERAGE</div>
            <div className="grid grid-cols-2 gap-3">
              {/* $ASTS — LIVE */}
              <Link href="/asts" className="group border border-white/10 px-5 py-4 hover:border-white/20 transition-colors block">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[12px] text-white/80 tracking-wider">$ASTS</span>
                  <span className="text-[6px] text-[#22C55E]/80 tracking-[0.15em] border border-[#22C55E]/30 px-1.5 py-0.5">
                    LIVE
                  </span>
                </div>
                <div className="text-[9px] text-white/35">Spacemob Terminal</div>
                <div className="text-[7px] text-white/18 mt-0.5">Direct-to-cell satellite broadband</div>
                <div className="flex items-center gap-3 mt-3 pt-3 border-t border-white/[0.06]">
                  {[
                    { value: '7', label: 'SATELLITES' },
                    { value: '307', label: 'PATENTS' },
                    { value: '4.5K+', label: 'FILINGS' },
                    { value: '13K+', label: 'DOCUMENTS' },
                  ].map((s) => (
                    <div key={s.label} className="text-center">
                      <div className="text-[12px] font-extralight text-white/60 tabular-nums">{s.value}</div>
                      <div className="text-[5px] text-white/18 tracking-[0.1em]">{s.label}</div>
                    </div>
                  ))}
                </div>
                <div className="mt-3 text-[8px] text-white/30 tracking-wider group-hover:text-white/60 transition-colors">
                  ENTER TERMINAL &rarr;
                </div>
              </Link>

              {/* $SPACE — Coming Soon */}
              <div className="border border-white/10 px-5 py-4 opacity-60">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[12px] text-white/80 tracking-wider">$SPACE</span>
                  <span className="text-[6px] text-[#FF6B35]/60 tracking-[0.15em] border border-[#FF6B35]/25 px-1.5 py-0.5">
                    COMING SOON
                  </span>
                </div>
                <div className="text-[9px] text-white/35">Sector Dashboard</div>
                <div className="text-[7px] text-white/18 mt-0.5">Cross-company analysis, sector flows, launch cadence</div>
                <div className="flex items-center gap-3 mt-3 pt-3 border-t border-white/[0.06]">
                  {[
                    { value: '12+', label: 'TICKERS' },
                    { value: '$626B', label: 'ECONOMY' },
                    { value: '150+', label: 'LAUNCHES/YR' },
                    { value: '6', label: 'SUBSECTORS' },
                  ].map((s) => (
                    <div key={s.label} className="text-center">
                      <div className="text-[12px] font-extralight text-white/60 tabular-nums">{s.value}</div>
                      <div className="text-[5px] text-white/18 tracking-[0.1em]">{s.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Quick nav */}
          <div className="mb-8">
            <div className="text-[7px] text-white/20 tracking-[0.2em] mb-3">EXPLORE</div>
            <div className="border border-white/[0.06] px-4 py-3 mb-2 flex items-center justify-between opacity-50 cursor-default">
              <div>
                <div className="text-[10px] text-white/40 tracking-wider">
                  THE BRIEFING
                </div>
                <div className="text-[7px] text-white/20">Cross-thread situation report</div>
              </div>
              <span className="text-[7px] text-white/20 tracking-[0.15em] shrink-0 ml-4">SOON</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {[
                { href: '/signals', label: 'SIGNALS', sublabel: 'Intelligence feed' },
                { href: '/horizon', label: 'HORIZON', sublabel: 'Upcoming events' },
                { href: '/thesis', label: 'THESIS', sublabel: 'Bull/bear cases' },
                { href: '/patents', label: 'PATENTS', sublabel: '307 patents' },
                { href: '/research', label: 'RESEARCH', sublabel: 'AI search' },
                { href: '/orbital', label: 'ORBITAL', sublabel: 'Constellation' },
                { href: '/regulatory', label: 'REGULATORY', sublabel: 'FCC battlemap' },
                { href: '/competitive', label: 'WAR ROOM', sublabel: 'D2C landscape' },
                { href: '/earnings', label: 'EARNINGS', sublabel: 'Call transcripts' },
              ].map((nav) =>
                LIVE_ROUTES.has(nav.href) ? (
                  <Link
                    key={nav.href}
                    href={nav.href}
                    className="border border-white/[0.06] px-3 py-2.5 hover:border-white/15 transition-colors group"
                  >
                    <div className="text-[9px] text-white/50 tracking-wider group-hover:text-white/80 transition-colors">
                      {nav.label}
                    </div>
                    <div className="text-[7px] text-white/18">{nav.sublabel}</div>
                  </Link>
                ) : (
                  <div
                    key={nav.href}
                    className="border border-white/[0.04] px-3 py-2.5 cursor-default opacity-50"
                  >
                    <div className="text-[9px] text-white/30 tracking-wider flex items-center gap-1">
                      {nav.label} <span className="text-[6px] text-white/20">SOON</span>
                    </div>
                    <div className="text-[7px] text-white/15">{nav.sublabel}</div>
                  </div>
                )
              )}
            </div>
          </div>

          {/* Email capture */}
          <div className="max-w-xs mx-auto">
            <EmailSignupForm />
          </div>

          {/* Login link */}
          <div className="text-center mt-4">
            <span className="text-[8px] text-white/15 tracking-wider cursor-default">
              EXISTING USER? LOG IN <span className="text-[6px]">SOON</span>
            </span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-center gap-3 pb-3">
        <a
          href="https://x.com/shortgravitycap"
          target="_blank"
          rel="noopener noreferrer"
          className="text-white/15 hover:text-white/40 transition-colors"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
            <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
          </svg>
        </a>
      </div>
      <div className="flex flex-wrap justify-center gap-x-3 gap-y-1 pb-6">
        {['CELESTRAK', 'SPACE-TRACK', 'SEC EDGAR', 'FCC', 'USPTO', 'EPO', 'FINNHUB'].map((src) => (
          <span key={src} className="text-[7px] text-white/12 tracking-[0.15em]">{src}</span>
        ))}
      </div>
    </div>
  )
}
