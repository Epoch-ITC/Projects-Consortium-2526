import { createServerClient } from '@supabase/ssr'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url)
    const code = searchParams.get('code')
    const next = searchParams.get('next') ?? '/dashboard'

    // Determine the real external origin — request.url is localhost when behind a proxy
    const forwardedHost = request.headers.get('x-forwarded-host')
    const forwardedProto = request.headers.get('x-forwarded-proto') ?? 'https'
    const hostHeader = request.headers.get('host')

    let externalOrigin: string
    if (forwardedHost) {
        externalOrigin = `${forwardedProto}://${forwardedHost}`
    } else if (hostHeader && !hostHeader.includes('localhost')) {
        externalOrigin = `https://${hostHeader}`
    } else {
        // Absolute fallback — use the parsed origin (will be localhost in dev)
        externalOrigin = new URL(request.url).origin
    }

    if (code) {
        const nextUrl = `${externalOrigin}${next}`

        // Create the response object (Using 303 See Other for standard redirect behavior)
        const response = new NextResponse(null, {
            status: 303,
            headers: { Location: nextUrl },
        })

        // Buffer for cookies to ensure they are captured before response
        const cookieBatch: { name: string; value: string; options: any }[] = []

        const supabase = createServerClient(
            process.env.NEXT_PUBLIC_SUPABASE_URL!,
            process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
            {
                cookies: {
                    getAll() {
                        const all: { name: string; value: string }[] = []
                        const cookieHeader = request.headers.get('cookie')
                        if (cookieHeader) {
                            cookieHeader.split(';').forEach(c => {
                                const parts = c.trim().split('=')
                                if (parts.length === 2) {
                                    all.push({ name: parts[0], value: parts[1] })
                                }
                            })
                        }
                        return all
                    },
                    setAll(cookiesToSet) {
                        // Capture cookies in buffer instead of writing directly to header immediately
                        cookiesToSet.forEach((c) => cookieBatch.push(c))
                    },
                },
            }
        )

        // Exchange code for session
        const { error } = await supabase.auth.exchangeCodeForSession(code)

        // Explicitly wait for Auth state change events to fire and populate the buffer
        await supabase.auth.getSession()
        await new Promise(resolve => setTimeout(resolve, 100))

        if (!error) {
            // Apply buffered cookies to the response
            cookieBatch.forEach(({ name, value, options }) => {
                response.cookies.set(name, value, {
                    ...options,
                    secure: request.url.startsWith('https://') || request.headers.get('x-forwarded-proto') === 'https'
                })
            })
            return response
        }
    }

    // Handle errors
    return new NextResponse(null, {
        status: 303,
        headers: { Location: `${externalOrigin}/auth/auth-code-error` }
    })
}
