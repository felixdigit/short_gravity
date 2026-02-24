import type { CommandItem } from './types'

export const STATIC_COMMANDS: CommandItem[] = [
  // Navigation — only pages that actually exist
  { id: 'nav-home', category: 'navigation', label: 'HOME', sublabel: 'Landing page', action: { type: 'navigate', href: '/' } },
  { id: 'nav-terminal', category: 'navigation', label: 'TERMINAL', sublabel: 'Spacemob Terminal — immersive view', action: { type: 'navigate', href: '/asts' } },
  { id: 'nav-signals', category: 'navigation', label: 'INTELLIGENCE FEED', sublabel: 'Cross-source signals + analysis', action: { type: 'navigate', href: '/signals' } },
  { id: 'nav-orbital', category: 'navigation', label: 'ORBITAL INTELLIGENCE', sublabel: 'Constellation health, orbital analysis', action: { type: 'navigate', href: '/orbital' } },

  // Presets
  { id: 'preset-default', category: 'preset', label: 'DEFAULT PRESET', sublabel: 'Standard terminal layout', action: { type: 'preset', presetId: 'default' } },
  { id: 'preset-launch', category: 'preset', label: 'LAUNCH DAY PRESET', sublabel: 'Launch countdown + signals focus', action: { type: 'preset', presetId: 'launch-day' } },
  { id: 'preset-unfold', category: 'preset', label: 'POST UNFOLD PRESET', sublabel: 'Regulatory + signal monitoring', action: { type: 'preset', presetId: 'post-unfold' } },
  { id: 'preset-earnings', category: 'preset', label: 'EARNINGS WEEK PRESET', sublabel: 'Financial metrics focus', action: { type: 'preset', presetId: 'earnings-week' } },

  // Actions
  { id: 'action-brain', category: 'action', label: 'SEARCH BRAIN', sublabel: 'Open AI-powered document search', action: { type: 'open-brain' } },
  { id: 'action-orbits', category: 'action', label: 'TOGGLE ORBITS', sublabel: 'Show/hide orbital paths', action: { type: 'toggle', key: 'showOrbits' } },
  { id: 'action-coverage', category: 'action', label: 'TOGGLE COVERAGE', sublabel: 'Show/hide coverage zones', action: { type: 'toggle', key: 'showCoverage' } },
  { id: 'action-mode', category: 'action', label: 'TOGGLE DISPLAY MODE', sublabel: 'Switch between minimal and dense', action: { type: 'toggle', key: 'mode' } },
]

export function filterCommands(query: string): CommandItem[] {
  if (!query) return STATIC_COMMANDS
  const lower = query.toLowerCase()
  return STATIC_COMMANDS.filter(cmd => {
    const haystack = `${cmd.label} ${cmd.sublabel || ''}`.toLowerCase()
    return haystack.includes(lower)
  })
}
