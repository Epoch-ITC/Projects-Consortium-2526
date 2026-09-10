import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createClient(cookieStore?: Awaited<ReturnType<typeof cookies>>) {
    const store = cookieStore || await cookies()

    return createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() {
                    return store.getAll()
                },
                setAll(cookiesToSet) {
                    console.log("SupabaseServer: NODE_ENV:", process.env.NODE_ENV)
                    console.log("SupabaseServer: setAll called with", cookiesToSet.map(c => ({ name: c.name, options: c.options })))
                    cookiesToSet.forEach(({ name, value, options }) => {
                        console.log(`SupabaseServer: Setting cookie ${name}`)
                        store.set(name, value, {
                            ...options,
                            secure: false, // FORCE FALSE FOR DEBUGGING
                        })
                    })
                },
            },
        }
    )
}
