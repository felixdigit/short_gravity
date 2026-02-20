export const dynamic = 'force-dynamic'

import type { Metadata } from 'next'
import { Inter, JetBrains_Mono } from 'next/font/google'
import { Providers } from './providers'
import { GlobalFrame } from '@/components/frame/GlobalFrame'
import { CommandPalette } from '@/components/command-palette/CommandPalette'
import { ClearanceModal } from '@/components/hud/overlays/ClearanceModal'
import './globals.css'

const inter = Inter({
  variable: '--font-inter',
  subsets: ['latin'],
})

const jetbrainsMono = JetBrains_Mono({
  variable: '--font-jetbrains-mono',
  subsets: ['latin'],
  weight: ['400', '500', '700'],
})

export const metadata: Metadata = {
  icons: {
    icon: '/favicon.svg',
  },
  title: 'Short Gravity',
  description: 'Real-time orbital tracking, patent mapping, and AI-powered intelligence for the space economy. 307 patents, 4,500+ regulatory filings, 13,000+ embedded documents.',
  metadataBase: new URL('https://shortgravity.com'),
  openGraph: {
    title: 'Short Gravity — Space Sector Intelligence',
    description: 'Real-time orbital tracking, patent mapping, and AI-powered cross-source analysis for the space economy.',
    url: 'https://shortgravity.com',
    siteName: 'Short Gravity',
    type: 'website',
    locale: 'en_US',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Short Gravity — Space Sector Intelligence',
    description: 'Real-time orbital tracking, patent mapping, and AI-powered cross-source analysis for the space economy.',
    creator: '@shortgravitycap',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} antialiased bg-[#0A0A0A] text-gray-100`}
      >
        <Providers>
          <GlobalFrame>
            {children}
          </GlobalFrame>
          <CommandPalette />
          <ClearanceModal />
        </Providers>
      </body>
    </html>
  )
}
