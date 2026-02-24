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

interface SignalAlertProps {
  signal: {
    severity: string
    title: string
    signal_type: string
    category: string
    description: string
    detected_at: string
    source_refs?: Array<{ table: string; id: string; title: string }>
  }
  unsubscribeUrl?: string
}

const SEVERITY_LABELS: Record<string, string> = {
  critical: 'CRITICAL',
  high: 'HIGH',
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#EF4444',
  high: '#FF6B35',
}

const CATEGORY_LABELS: Record<string, string> = {
  market: 'MARKET',
  regulatory: 'REGULATORY',
  community: 'COMMUNITY',
  corporate: 'CORPORATE',
  ip: 'INTELLECTUAL PROPERTY',
  constellation: 'CONSTELLATION',
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone: 'America/New_York',
    timeZoneName: 'short',
  })
}

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://shortgravity.com'

export default function SignalAlert({ signal, unsubscribeUrl }: SignalAlertProps) {
  const severityLabel = SEVERITY_LABELS[signal.severity] || signal.severity.toUpperCase()
  const severityColor = SEVERITY_COLORS[signal.severity] || '#FF6B35'
  const categoryLabel = CATEGORY_LABELS[signal.category] || signal.category?.toUpperCase() || ''

  return (
    <Html lang="en">
      <Head>
        <Font fontFamily="JetBrains Mono" fallbackFontFamily="monospace" webFont={{
          url: 'https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&display=swap',
          format: 'woff2',
        }} />
      </Head>
      <Preview>{severityLabel} ALERT — {signal.title}</Preview>
      <Body style={body}>
        <Container style={container}>
          {/* Header */}
          <Section style={header}>
            <Text style={logoText}>SHORT GRAVITY</Text>
            <Text style={{ ...alertBadge, backgroundColor: severityColor }}>
              {severityLabel} ALERT
            </Text>
          </Section>

          <Hr style={divider} />

          {/* Signal */}
          <Section style={section}>
            <Text style={categoryText}>{categoryLabel}</Text>
            <Text style={titleText}>{signal.title}</Text>
            <Text style={timeText}>{formatTime(signal.detected_at)}</Text>
          </Section>

          {/* Description */}
          <Section style={section}>
            <Text style={descriptionText}>{signal.description}</Text>
          </Section>

          {/* Sources */}
          {signal.source_refs && signal.source_refs.length > 0 && (
            <Section style={section}>
              <Text style={sectionLabel}>SOURCES</Text>
              {signal.source_refs.map((ref, i) => (
                <Text key={i} style={sourceRow}>
                  {ref.title}
                </Text>
              ))}
            </Section>
          )}

          <Hr style={divider} />

          {/* CTA */}
          <Section style={{ textAlign: 'center' as const, padding: '24px 0' }}>
            <Link href={`${siteUrl}/signals`} style={ctaButton}>
              VIEW IN TERMINAL
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

// Styles — matching DailyBrief HUD aesthetic
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
  margin: '0 0 12px',
}

const alertBadge = {
  color: '#FFFFFF',
  fontSize: '10px',
  fontWeight: 700,
  letterSpacing: '2px',
  padding: '6px 16px',
  display: 'inline-block' as const,
}

const divider = {
  borderColor: 'rgba(255,255,255,0.06)',
  margin: '16px 0',
}

const section = {
  padding: '12px 0',
}

const categoryText = {
  color: '#71717A',
  fontSize: '9px',
  fontWeight: 500,
  letterSpacing: '2px',
  textTransform: 'uppercase' as const,
  margin: '0 0 4px',
}

const titleText = {
  color: '#FFFFFF',
  fontSize: '18px',
  fontWeight: 400,
  lineHeight: '26px',
  margin: '0 0 8px',
}

const timeText = {
  color: '#71717A',
  fontSize: '10px',
  letterSpacing: '1px',
  margin: 0,
}

const descriptionText = {
  color: '#E5E7EB',
  fontSize: '12px',
  lineHeight: '20px',
  margin: '4px 0',
}

const sectionLabel = {
  color: '#71717A',
  fontSize: '9px',
  fontWeight: 500,
  letterSpacing: '2px',
  textTransform: 'uppercase' as const,
  margin: '0 0 8px',
}

const sourceRow = {
  color: '#E5E7EB',
  fontSize: '11px',
  lineHeight: '18px',
  margin: '4px 0',
  paddingLeft: '8px',
  borderLeft: '2px solid rgba(255,255,255,0.1)',
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
