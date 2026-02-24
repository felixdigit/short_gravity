export type CommandCategory = 'navigation' | 'search' | 'satellite' | 'preset' | 'action'

export type CommandAction =
  | { type: 'navigate'; href: string }
  | { type: 'preset'; presetId: string }
  | { type: 'toggle'; key: string }
  | { type: 'open-brain'; query?: string }
  | { type: 'select-satellite'; noradId: string }
  | { type: 'external'; url: string }

export interface CommandItem {
  id: string
  category: CommandCategory
  label: string
  sublabel?: string
  badge?: string
  action: CommandAction
  relevance?: number
}
