"use client"
import Link from "next/link"
import { GraduationCap, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { useAuth } from "@/context/AuthContext"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"

export default function LoginPage() {
    const { signInWithGoogle, user } = useAuth()
    const [isLoading, setIsLoading] = useState(false)
    const router = useRouter()

    useEffect(() => {
        document.title = "Login - Student Helper"
    }, [])

    if (user) {
        router.push('/dashboard')
        return null
    }

    const handleGoogleLogin = async () => {
        console.log("Login button clicked")
        try {
            setIsLoading(true)
            console.log("Calling signInWithGoogle...")
            await signInWithGoogle()
            console.log("signInWithGoogle called successfully")
        } catch (error) {
            console.error("Login failed:", error)
            alert(`Login failed: ${error instanceof Error ? error.message : "Unknown error"}`)
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="flex min-h-screen bg-slate-950 text-white">
            {/* Left Panel - Hero/Decor */}
            <div className="hidden lg:flex w-1/2 flex-col justify-between p-12 relative overflow-hidden bg-slate-900">
                <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1541339907198-e08756dedf3f?q=80&w=2070&auto=format&fit=crop')] bg-cover bg-center opacity-20"></div>
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent"></div>

                <div className="relative z-10">
                    {/* Logo */}
                </div>

                <div className="relative z-10 max-w-lg">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="p-2 bg-blue-600 rounded-lg">
                            <GraduationCap className="h-6 w-6 text-white" />
                        </div>
                        <h1 className="font-bold text-xl">Student AI Helper</h1>
                    </div>
                    <h1 className="text-4xl font-bold tracking-tight mb-4 leading-tight">
                        Elevate Your <br />
                        Academic Journey
                    </h1>
                    <p className="text-slate-400 text-lg">
                        Your personal AI assistant for scheduling, study plans, and research. Simplify your student life today.
                    </p>

                    <div className="flex gap-2 mt-8">
                        <div className="h-1.5 w-8 bg-blue-600 rounded-full"></div>
                        <div className="h-1.5 w-2 bg-slate-700 rounded-full"></div>
                        <div className="h-1.5 w-2 bg-slate-700 rounded-full"></div>
                    </div>
                </div>
            </div>

            {/* Right Panel - Login Form */}
            <div className="flex w-full lg:w-1/2 items-center justify-center p-8">
                <div className="w-full max-w-md space-y-8">
                    <div className="space-y-2">
                        <h2 className="text-3xl font-bold">Log in to your account</h2>
                        <p className="text-slate-400">Welcome back! Please enter your details.</p>
                    </div>

                    <div className="space-y-4">
                        <div className="space-y-2">
                            <label htmlFor="email" className="text-sm font-medium">Email</label>
                            <Input id="email" placeholder="student@university.edu" type="email" />
                        </div>
                        <div className="space-y-2">
                            <div className="flex justify-between items-center">
                                <label htmlFor="password" className="text-sm font-medium">Password</label>
                                <Link href="#" className="text-sm text-blue-500 hover:text-blue-400">Forgot password?</Link>
                            </div>
                            <Input id="password" placeholder="Enter your password" type="password" />
                        </div>

                        <Button className="w-full bg-blue-600 hover:bg-blue-700">Sign In</Button>
                    </div>

                    <div className="relative">
                        <div className="absolute inset-0 flex items-center">
                            <span className="w-full border-t border-slate-800" />
                        </div>
                        <div className="relative flex justify-center text-xs uppercase">
                            <span className="bg-slate-950 px-2 text-slate-500">Or continue with</span>
                        </div>
                    </div>

                    <Button
                        variant="outline"
                        className="w-full border-slate-700 bg-slate-900 hover:bg-slate-800 hover:text-white"
                        onClick={handleGoogleLogin}
                        disabled={isLoading}
                    >
                        {isLoading ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                            <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
                                <path
                                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                                    fill="#4285F4"
                                />
                                <path
                                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                                    fill="#34A853"
                                />
                                <path
                                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                                    fill="#FBBC05"
                                />
                                <path
                                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                                    fill="#EA4335"
                                />
                            </svg>
                        )}
                        Google
                    </Button>

                    <p className="text-center text-sm text-slate-400">
                        Don't have an account?{" "}
                        <Link href="#" className="font-semibold text-blue-500 hover:text-blue-400">
                            Sign up for free
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
