"use client"

import { useEffect, useState, useCallback } from "react"
import { API_URL } from "@/lib/utils"
import { useAuth } from "@/context/AuthContext"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Mail, ExternalLink, Clock, Tag, RefreshCw } from "lucide-react"
import { useRouter } from "next/navigation"

interface ImportantEmail {
    id: string
    subject: string
    sender: string
    matched_rule: string
    gmail_link: string
    received_at: string
    created_at: string
}

export default function DashboardPage() {
    const { user, session } = useAuth()
    const router = useRouter()
    const [importantEmails, setImportantEmails] = useState<ImportantEmail[]>([])
    const [loading, setLoading] = useState(true)
    const [syncing, setSyncing] = useState(false)
    const [toast, setToast] = useState<{ message: string, type: 'success' | 'error' } | null>(null)
    const [selectedDays, setSelectedDays] = useState(4)
    const [hasAutoSynced, setHasAutoSynced] = useState(false)

    useEffect(() => {
        document.title = "Dashboard - Student Helper"
    }, [])

    const showToast = (message: string, type: 'success' | 'error' = 'success') => {
        setToast({ message, type })
        setTimeout(() => setToast(null), 3000)
    }

    const fetchImportantEmails = useCallback(async () => {
        if (!session?.access_token) {
            setLoading(false)
            return
        }

        try {
            setLoading(true)
            const res = await fetch(`${API_URL}/gmail/important`, {
                headers: {
                    "Authorization": `Bearer ${session.access_token}`
                }
            })
            if (res.ok) {
                const data = await res.json()
                setImportantEmails(data.emails || [])
            }
        } catch (e) {
            console.error("Failed to fetch important emails", e)
        } finally {
            setLoading(false)
        }
    }, [session?.access_token])

    useEffect(() => {
        if (user && session) {
            fetchImportantEmails()
        }
    }, [user, session, fetchImportantEmails])

    // Auto-sync on login (4 days)
    useEffect(() => {
        if (user && session && !hasAutoSynced) {
            const autoSync = async () => {
                try {
                    const res = await fetch(`${API_URL}/gmail/sync?days_back=4`, {
                        method: "POST",
                        headers: {
                            "Authorization": `Bearer ${session?.access_token}`
                        }
                    })
                    if (res.ok) {
                        setHasAutoSynced(true)
                        setTimeout(() => fetchImportantEmails(), 3000)
                    }
                } catch (e) {
                    console.error("Auto-sync failed", e)
                }
            }
            autoSync()
        }
    }, [user, session, hasAutoSynced, session?.access_token, fetchImportantEmails])

    const handleSync = async () => {
        try {
            setSyncing(true)
            const res = await fetch(`${API_URL}/gmail/sync?days_back=4`, {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${session?.access_token}`
                }
            })

            if (res.ok) {
                showToast("Sync started! Emails will appear shortly.", 'success')
                setTimeout(() => {
                    fetchImportantEmails()
                }, 3000)
            } else {
                showToast("Sync failed. Please make sure Gmail is connected.", 'error')
            }
        } catch (e) {
            console.error("Sync failed", e)
            showToast("Sync failed. Please try again.", 'error')
        } finally {
            setSyncing(false)
        }
    }

    const formatDate = (dateStr: string) => {
        if (!dateStr) return "Unknown date"
        const date = new Date(dateStr)
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
        const diffDays = Math.floor(diffHours / 24)

        if (diffHours < 1) return "Just now"
        if (diffHours < 24) return `${diffHours}h ago`
        if (diffDays < 7) return `${diffDays}d ago`
        return date.toLocaleDateString()
    }

    const getRuleBadgeColor = (rule: string) => {
        if (rule.includes("AIMS")) return "bg-purple-500/10 text-purple-500 border-purple-500/20"
        if (rule.includes("NSS")) return "bg-blue-500/10 text-blue-500 border-blue-500/20"
        return "bg-green-500/10 text-green-500 border-green-500/20"
    }

    const userName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || "Student"

    return (
        <div className="space-y-8">
            {/* Hero Section */}
            <div className="space-y-2">
                <h1 className="text-3xl font-bold">Welcome back, {userName}</h1>
                <p className="text-slate-400">
                    Here's what needs your attention today
                </p>
            </div>

            {/* Important Emails Section */}
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-2xl font-semibold flex items-center gap-2">
                        <Mail className="h-6 w-6 text-red-500" />
                        Important Emails
                    </h2>
                    <div className="flex gap-2">
                        <select
                            value={selectedDays}
                            onChange={(e) => setSelectedDays(Number(e.target.value))}
                            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm hover:border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            {[1, 2, 3, 4, 5, 6, 7].map(days => (
                                <option key={days} value={days}>
                                    {days} day{days > 1 ? 's' : ''}
                                </option>
                            ))}
                        </select>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={handleSync}
                            disabled={syncing}
                            className="border-slate-700 hover:bg-slate-800"
                        >
                            <RefreshCw className={`h-4 w-4 mr-2 ${syncing ? 'animate-spin' : ''}`} />
                            {syncing ? "Syncing..." : "Sync"}
                        </Button>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => router.push('/dashboard/integrations')}
                            className="border-slate-700 hover:bg-slate-800"
                        >
                            Manage Integrations
                        </Button>
                    </div>
                </div>

                {loading ? (
                    <div className="text-center py-12 text-slate-400">
                        <div className="animate-pulse">Loading emails...</div>
                    </div>
                ) : importantEmails.length === 0 ? (
                    <Card className="bg-slate-900/50 border-slate-800">
                        <CardContent className="py-12 text-center">
                            <Mail className="h-12 w-12 text-slate-600 mx-auto mb-4" />
                            <h3 className="text-lg font-medium text-slate-300 mb-2">No Important Emails</h3>
                            <p className="text-slate-500 mb-4">
                                Connect Gmail to see important notifications here
                            </p>
                            <Button
                                onClick={() => router.push('/dashboard/integrations')}
                                className="bg-blue-600 hover:bg-blue-700"
                            >
                                Connect Gmail
                            </Button>
                        </CardContent>
                    </Card>
                ) : (
                    <div className="grid gap-4">
                        {importantEmails.slice(0, 10).map((email) => (
                            <Card
                                key={email.id}
                                className="bg-slate-900/50 border-slate-800 hover:border-slate-700 transition-all"
                            >
                                <CardHeader>
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex-1 min-w-0">
                                            <CardTitle className="text-lg mb-2 truncate">
                                                {email.subject}
                                            </CardTitle>
                                            <CardDescription className="flex flex-wrap items-center gap-2">
                                                <span className="text-slate-500 truncate">
                                                    From: {email.sender}
                                                </span>
                                            </CardDescription>
                                        </div>
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            className="border-slate-700 hover:bg-slate-800 shrink-0"
                                            onClick={() => window.open(email.gmail_link, '_blank')}
                                        >
                                            <ExternalLink className="h-4 w-4 mr-1" />
                                            Open
                                        </Button>
                                    </div>
                                    <div className="flex flex-wrap items-center gap-2 mt-3">
                                        <span className={`text-xs px-2 py-1 rounded-full border ${getRuleBadgeColor(email.matched_rule)}`}>
                                            <Tag className="h-3 w-3 inline mr-1" />
                                            {email.matched_rule}
                                        </span>
                                        <span className="text-xs text-slate-500 flex items-center gap-1">
                                            <Clock className="h-3 w-3" />
                                            {formatDate(email.received_at || email.created_at)}
                                        </span>
                                    </div>
                                </CardHeader>
                            </Card>
                        ))}
                    </div>
                )}
            </div>

            {/* Additional Info Section */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="bg-gradient-to-br from-blue-900/20 to-blue-950/10 border-blue-900/50">
                    <CardHeader>
                        <CardTitle className="text-blue-400">Quick Stats</CardTitle>
                        <CardDescription className="text-3xl font-bold text-white mt-2">
                            {importantEmails.length}
                        </CardDescription>
                        <CardDescription className="text-slate-400">
                            Important notifications
                        </CardDescription>
                    </CardHeader>
                </Card>
            </div>

            {/* Toast Notification */}
            {toast && (
                <div className={`fixed bottom-6 right-6 px-6 py-4 rounded-lg shadow-lg border animate-in slide-in-from-bottom-5 ${toast.type === 'success'
                    ? 'bg-green-900/90 border-green-700 text-green-100'
                    : 'bg-red-900/90 border-red-700 text-red-100'
                    }`}>
                    <div className="flex items-center gap-3">
                        {toast.type === 'success' ? (
                            <div className="h-5 w-5 rounded-full bg-green-500 flex items-center justify-center">
                                <span className="text-white text-xs">✓</span>
                            </div>
                        ) : (
                            <div className="h-5 w-5 rounded-full bg-red-500 flex items-center justify-center">
                                <span className="text-white text-xs">!</span>
                            </div>
                        )}
                        <p className="font-medium">{toast.message}</p>
                    </div>
                </div>
            )}
        </div>
    )
}
