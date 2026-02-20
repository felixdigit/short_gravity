import { cn } from '../../lib/utils'

type TextVariant = 'primary' | 'secondary' | 'muted' | 'dim' | 'label' | 'value' | 'accent'
type TextSize = 'xs' | 'sm' | 'base' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl'

interface TextProps {
  children: React.ReactNode
  variant?: TextVariant
  size?: TextSize
  mono?: boolean
  uppercase?: boolean
  tracking?: 'normal' | 'wide' | 'wider' | 'widest'
  tabular?: boolean
  className?: string
  as?: 'span' | 'div' | 'p'
}

const variantStyles: Record<TextVariant, string> = {
  primary: 'text-white',
  secondary: 'text-white/90',
  muted: 'text-white/50',
  dim: 'text-white/30',
  label: 'text-white/50',
  value: 'text-white/90',
  accent: 'text-amber-400',
}

const sizeStyles: Record<TextSize, string> = {
  xs: 'text-[6px]',
  sm: 'text-[7px]',
  base: 'text-[8px]',
  lg: 'text-[9px]',
  xl: 'text-[10px]',
  '2xl': 'text-[11px]',
  '3xl': 'text-[14px]',
  '4xl': 'text-[28px]',
}

const trackingStyles: Record<string, string> = {
  normal: 'tracking-normal',
  wide: 'tracking-wide',
  wider: 'tracking-wider',
  widest: 'tracking-[0.2em]',
}

export function Text({
  children,
  variant = 'primary',
  size = 'base',
  mono = true,
  uppercase = false,
  tracking = 'normal',
  tabular = false,
  className,
  as: Component = 'span',
}: TextProps) {
  return (
    <Component
      className={cn(
        variantStyles[variant],
        sizeStyles[size],
        trackingStyles[tracking],
        mono && 'font-mono',
        uppercase && 'uppercase',
        tabular && 'tabular-nums',
        className
      )}
    >
      {children}
    </Component>
  )
}

export function Label({ children, className, ...props }: Omit<TextProps, 'variant' | 'size' | 'uppercase' | 'tracking'>) {
  return (
    <Text
      variant="label"
      size="base"
      uppercase
      tracking="wider"
      className={className}
      {...props}
    >
      {children}
    </Text>
  )
}

export function Value({ children, className, size = 'lg', ...props }: Omit<TextProps, 'variant'>) {
  return (
    <Text
      variant="value"
      size={size}
      tabular
      className={className}
      {...props}
    >
      {children}
    </Text>
  )
}

export function Muted({ children, className, ...props }: Omit<TextProps, 'variant'>) {
  return (
    <Text variant="muted" className={className} {...props}>
      {children}
    </Text>
  )
}
