import { cn } from '../../lib/utils'

interface PanelProps {
  children: React.ReactNode
  className?: string
  blur?: boolean
  border?: boolean
}

interface PanelHeaderProps {
  children: React.ReactNode
  className?: string
  action?: React.ReactNode
}

interface PanelContentProps {
  children: React.ReactNode
  className?: string
  scroll?: boolean
}

export function Panel({ children, className, blur = true, border = true }: PanelProps) {
  return (
    <div
      className={cn(
        'bg-black/30 font-mono',
        blur && 'backdrop-blur-sm',
        border && 'border border-white/[0.06]',
        className
      )}
    >
      {children}
    </div>
  )
}

Panel.Header = function PanelHeader({ children, className, action }: PanelHeaderProps) {
  return (
    <div className={cn('flex items-center justify-between', className)}>
      <div className="text-[8px] text-white/50 tracking-wider uppercase">{children}</div>
      {action}
    </div>
  )
}

Panel.Content = function PanelContent({ children, className, scroll = false }: PanelContentProps) {
  return (
    <div
      className={cn(
        scroll && 'overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent',
        className
      )}
    >
      {children}
    </div>
  )
}

Panel.Divider = function PanelDivider({ className }: { className?: string }) {
  return <div className={cn('border-t border-white/10', className)} />
}

Panel.Section = function PanelSection({
  children,
  className,
  title,
}: {
  children: React.ReactNode
  className?: string
  title?: string
}) {
  return (
    <div className={cn('pt-3 border-t border-white/10', className)}>
      {title && (
        <div className="text-[8px] text-white/50 tracking-wider uppercase mb-2">{title}</div>
      )}
      {children}
    </div>
  )
}
