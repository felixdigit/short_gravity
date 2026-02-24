import { createClient } from '@supabase/supabase-js'

function getBrowserClient() {
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}

export async function signInWithEmail(email: string) {
  const supabase = getBrowserClient()
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: {
      emailRedirectTo: `${window.location.origin}/account`,
    },
  })
  return { error }
}

export async function signOut() {
  const supabase = getBrowserClient()
  const { error } = await supabase.auth.signOut()
  return { error }
}

export async function getSession() {
  const supabase = getBrowserClient()
  const { data: { session }, error } = await supabase.auth.getSession()
  return { session, error }
}

export async function getUser() {
  const supabase = getBrowserClient()
  const { data: { user }, error } = await supabase.auth.getUser()
  return { user, error }
}
