export const dynamic = 'force-dynamic'

// Immersive layout — NO navbar, NO effects, pure black canvas
export default function ImmersiveLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="fixed inset-0 bg-black overflow-hidden">
      {children}
    </div>
  )
}
