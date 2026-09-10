"use client"

import { createContext, useContext, useEffect, useState, useRef } from 'react'
import { User, Session } from '@supabase/supabase-js'
import { createClient } from '@/utils/supabase/client'
import { useRouter } from 'next/navigation'

interface AuthContextType {
    user: User | null
    session: Session | null
    isLoading: boolean
    signInWithGoogle: () => Promise<void>

    signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Create Supabase client once at module level — prevents re-creation on every render
const supabase = createClient()

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [session, setSession] = useState<Session | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const router = useRouter()
    const currentTokenRef = useRef<string | null>(null)

    useEffect(() => {
        const { data: { subscription } } = supabase.auth.onAuthStateChange((event, newSession) => {
            const newToken = newSession?.access_token ?? null

            // On TOKEN_REFRESHED, skip state update if user hasn't changed
            // This prevents re-renders when the browser tab regains focus
            if (event === 'TOKEN_REFRESHED' && currentTokenRef.current && newToken) {
                currentTokenRef.current = newToken
                // Silently update session ref for future API calls without triggering re-render
                setSession(prev => {
                    if (prev) {
                        // Mutate in place to keep the same reference — no re-render
                        prev.access_token = newToken
                        return prev
                    }
                    return newSession
                })
                return
            }

            currentTokenRef.current = newToken
            setSession(newSession)
            setUser(newSession?.user ?? null)
            setIsLoading(false)

            if (event === 'SIGNED_IN') {
                router.refresh()
            }
        })

        return () => {
            subscription.unsubscribe()
        }
    }, [router])

    const signInWithGoogle = async () => {
        const { error } = await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: `${window.location.origin}/auth/callback`
            }
        })
        if (error) {
            console.error("signInWithOAuth error:", error)
            throw error
        }
    }

    const signOut = async () => {
        await supabase.auth.signOut()
        router.push('/login')
    }

    return (
        <AuthContext.Provider value={{ user, session, isLoading, signInWithGoogle, signOut }}>
            {children}
        </AuthContext.Provider>
    )
}

export const useAuth = () => {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
