import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
    let response = NextResponse.next({
        request: {
            headers: request.headers,
        },
    })

    const supabase = createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() {
                    return request.cookies.getAll()
                },
                setAll(cookiesToSet) {
                    cookiesToSet.forEach(({ name, value, options }) => request.cookies.set(name, value))
                    response = NextResponse.next({
                        request,
                    })
                    cookiesToSet.forEach(({ name, value, options }) =>
                        response.cookies.set(name, value, {
                            ...options,
                            secure: request.nextUrl.protocol === 'https:' || request.headers.get('x-forwarded-proto') === 'https'
                        })
                    )
                },
            },
        }
    )

    const {
        data: { user },
        error,
    } = await supabase.auth.getUser()

    console.log("Middleware: Path:", request.nextUrl.pathname)
    console.log("Middleware: Cookies:", request.cookies.getAll().map(c => c.name))
    console.log("Middleware: Test Cookie:", request.cookies.get('test-cookie')?.value)
    console.log("Middleware: User found:", !!user)
    if (error) console.log("Middleware: Auth Error:", error.message)

    // Determine real external origin for redirects behind proxy
    const forwardedHost = request.headers.get('x-forwarded-host')
    const forwardedProto = request.headers.get('x-forwarded-proto') ?? 'https'
    const hostHeader = request.headers.get('host')

    let externalBase: string
    if (forwardedHost) {
        externalBase = `${forwardedProto}://${forwardedHost}`
    } else if (hostHeader && !hostHeader.includes('localhost')) {
        externalBase = `https://${hostHeader}`
    } else {
        externalBase = request.url.split(request.nextUrl.pathname)[0]
    }

    if (request.nextUrl.pathname.startsWith('/dashboard') && !user) {
        console.log("Middleware: Redirecting to login")
        return NextResponse.redirect(new URL('/login', externalBase))
    }

    if (request.nextUrl.pathname === '/login' && user) {
        console.log("Middleware: Redirecting to dashboard")
        return NextResponse.redirect(new URL('/dashboard', externalBase))
    }

    return response
}

export const config = {
    matcher: [
        /*
         * Match all request paths except for the ones starting with:
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         * Feel free to modify this pattern to include more paths.
         */
        '/((?!_next/static|_next/image|favicon.ico|auth/callback|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
    ],
}
