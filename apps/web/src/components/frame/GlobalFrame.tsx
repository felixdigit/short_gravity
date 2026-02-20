'use client'

import { usePathname } from 'next/navigation'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'

type FrameMode = 'immersive' | 'landing' | 'standard'

function getFrameMode(pathname: string | null): FrameMode {
  if (!pathname) return 'standard'
  if (pathname === '/') return 'landing'
  if (pathname.startsWith('/asts')) return 'immersive'
  return 'standard'
}

export function GlobalFrame({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const mode = getFrameMode(pathname)

  if (mode === 'landing') {
    return <>{children}</>
  }

  if (mode === 'immersive') {
    return (
      <>
        <Sidebar mode="immersive" />
        <TopBar mode="immersive" />
        {children}
      </>
    )
  }

  return (
    <>
      <Sidebar mode="standard" />
      <TopBar mode="standard" />
      <main className="ml-12 mt-12">
        {children}
      </main>
    </>
  )
}
