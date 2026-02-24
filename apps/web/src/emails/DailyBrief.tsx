import {
  Html,
  Head,
  Body,
  Container,
  Section,
  Text,
  Link,
  Hr,
  Font,
  Preview,
} from '@react-email/components'

interface Signal {
  severity: string
  title: string
  signal_type: string
  detected_at: string
}

interface HorizonEvent {
  type: string
  title: string
  date: string
  severity: string
}

interface DailyBriefProps {
  date: string
  price?: { close: number; change: number; changePercent: number } | null
  signals: Signal[]
  horizonEvents: HorizonEvent[]
  newFilingsCount: number
  unsubscribeUrl?: string
}

const SEVERITY_DOTS: Record<string, string> = {
  critical: '🔴',
  high: '🟠',
  medium: '🟡',
  low: '⚪',
}

const EVENT_LABELS: Record<string, string> = {
  launch: 'LAUNCH',
  conjunction: 'CONJUNCTION',
  regulatory: 'REGULATORY',
  patent: 'PATENT',
  earnings: 'EARNINGS',
  catalyst: 'CATALYST',
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function daysUntil(iso: string): string {
  const diff = Math.ceil((new Date(iso).getTime() - Date.now()) / 86400000)
  if (diff === 0) return 'TODAY'
  if (diff === 1) return 'TOMORROW'
  return `T-${diff}D`
}

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://shortgravity.com'

export default function DailyBrief({
  date,
  price,
  signals,
  horizonEvents,
  newFilingsCount,
  unsubscribeUrl,
}: DailyBriefProps) {
  const hasContent = signals.length > 0 || horizonEvents.length > 0 || newFilingsCount > 0

  return (
    <Html lang="en">
      <Head>
        <Font fontFamily="JetBrains Mono" fallbackFontFamily="monospace" webFont={{
          url: 'https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&display=swap',
          format: 'woff2',
        }} />
      </Head>
      <Preview>Short Gravity Daily Brief — {date}</Preview>
      <Body style={body}>
        <Container style={container}>
          {/* Header */}
          <Section style={header}>
            <Text style={logoText}>SHORT GRAVITY</Text>
            <Text style={dateText}>DAILY BRIEF — {date}</Text>
          </Section>

          <Hr style={divider} />

          {/* Price Snapshot */}
          {price && (
            <Section style={section}>
              <Text style={sectionLabel}>$ASTS</Text>
              <Text style={priceValue}>
                ${price.close.toFixed(2)}
                <span style={price.change >= 0 ? priceUp : priceDown}>
                  {' '}{price.change >= 0 ? '+' : ''}{price.change.toFixed(2)} ({price.changePercent >= 0 ? '+' : ''}{price.changePercent.toFixed(1)}%)
                </span>
              </Text>
            </Section>
          )}

          {/* Signals */}
          {signals.length > 0 && (
            <Section style={section}>
              <Text style={sectionLabel}>INTELLIGENCE ({signals.length})</Text>
              {signals.map((s, i) => (
                <Text key={i} style={signalRow}>
                  {SEVERITY_DOTS[s.severity] || '⚪'} {s.title}
                </Text>
              ))}
            </Section>
          )}

          {/* Horizon */}
          {horizonEvents.length > 0 && (
            <Section style={section}>
              <Text style={sectionLabel}>HORIZON (NEXT 48H)</Text>
              {horizonEvents.map((e, i) => (
                <Text key={i} style={horizonRow}>
                  <span style={countdown}>{daysUntil(e.date)}</span>
                  {' '}<span style={eventBadge}>{EVENT_LABELS[e.type] || e.type.toUpperCase()}</span>
                  {' '}{e.title}
                </Text>
              ))}
            </Section>
          )}

          {/* Filings */}
          {newFilingsCount > 0 && (
            <Section style={section}>
              <Text style={sectionLabel}>NEW FILINGS</Text>
              <Text style={filingText}>{newFilingsCount} new filing{newFilingsCount > 1 ? 's' : ''} in the last 24 hours</Text>
            </Section>
          )}

          {/* Empty state */}
          {!hasContent && (
            <Section style={section}>
              <Text style={mutedText}>All systems nominal. No significant activity in the last 24 hours.</Text>
            </Section>
          )}

          <Hr style={divider} />

          {/* CTA */}
          <Section style={{ textAlign: 'center' as const, padding: '24px 0' }}>
            <Link href={`${siteUrl}/asts`} style={ctaButton}>
              OPEN TERMINAL
            </Link>
          </Section>

          {/* Footer */}
          <Section style={footer}>
            <Text style={footerText}>
              Short Gravity — Space Sector Intelligence
            </Text>
            {unsubscribeUrl && (
              <Text style={footerText}>
                <Link href={unsubscribeUrl} style={footerLink}>Unsubscribe</Link>
              </Text>
            )}
          </Section>
        </Container>
      </Body>
    </Html>
  )
}

// ============================================================================
// Styles — HUD aesthetic: black bg, white text, orange accents
// ============================================================================

const body = {
  backgroundColor: '#030305',
  fontFamily: "'JetBrains Mono', monospace",
  margin: 0,
  padding: 0,
}

const container = {
  maxWidth: '600px',
  margin: '0 auto',
  padding: '32px 24px',
}

const header = {
  textAlign: 'center' as const,
  padding: '0 0 16px',
}

const logoText = {
  color: '#FFFFFF',
  fontSize: '14px',
  fontWeight: 700,
  letterSpacing: '4px',
  margin: '0 0 4px',
}

const dateText = {
  color: '#71717A',
  fontSize: '10px',
  letterSpacing: '2px',
  margin: 0,
}

const divider = {
  borderColor: 'rgba(255,255,255,0.06)',
  margin: '16px 0',
}

const section = {
  padding: '12px 0',
}

const sectionLabel = {
  color: '#71717A',
  fontSize: '9px',
  fontWeight: 500,
  letterSpacing: '2px',
  textTransform: 'uppercase' as const,
  margin: '0 0 8px',
}

const priceValue = {
  color: '#FFFFFF',
  fontSize: '24px',
  fontWeight: 300,
  margin: '0',
}

const priceUp = {
  color: '#22C55E',
  fontSize: '14px',
}

const priceDown = {
  color: '#EF4444',
  fontSize: '14px',
}

const signalRow = {
  color: '#E5E7EB',
  fontSize: '12px',
  lineHeight: '20px',
  margin: '4px 0',
}

const horizonRow = {
  color: '#E5E7EB',
  fontSize: '12px',
  lineHeight: '20px',
  margin: '4px 0',
}

const countdown = {
  color: '#FF6B35',
  fontWeight: 500,
  fontSize: '10px',
}

const eventBadge = {
  color: '#71717A',
  fontSize: '9px',
  letterSpacing: '1px',
}

const filingText = {
  color: '#E5E7EB',
  fontSize: '12px',
  margin: '4px 0',
}

const mutedText = {
  color: '#71717A',
  fontSize: '12px',
  margin: '4px 0',
}

const ctaButton = {
  backgroundColor: '#FF6B35',
  color: '#FFFFFF',
  fontSize: '11px',
  fontWeight: 700,
  letterSpacing: '2px',
  textDecoration: 'none',
  padding: '12px 32px',
  display: 'inline-block' as const,
}

const footer = {
  textAlign: 'center' as const,
  padding: '16px 0 0',
}

const footerText = {
  color: '#71717A',
  fontSize: '9px',
  letterSpacing: '1px',
  margin: '4px 0',
}

const footerLink = {
  color: '#71717A',
  textDecoration: 'underline',
}
