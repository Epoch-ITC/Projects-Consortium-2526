"use client"

import { Search, Bell, GraduationCap, Mail, Calendar, ClipboardList, User } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/Card"
import { useAuth } from "@/context/AuthContext"
import { useSearchParams } from "next/navigation"
import { Suspense, useEffect, useState } from "react"
import { AimsConnectModal } from "@/components/aims/AimsConnectModal"
import { Loader2 } from "lucide-react"
import { API_URL } from "@/lib/utils"

export default function IntegrationsPage() {
    return (
        <Suspense fallback={<div className="flex h-full items-center justify-center"><Loader2 className="h-8 w-8 animate-spin text-purple-500" /></div>}>
            <IntegrationsContent />
        </Suspense>
    )
}

function IntegrationsContent() {
    const { user, session, signOut } = useAuth()
    const [connectedIntegrations, setConnectedIntegrations] = useState<any[]>([])
    const [isAimsModalOpen, setIsAimsModalOpen] = useState(false)
    const searchParams = useSearchParams()

    useEffect(() => {
        document.title = "Integrations - Student Helper"
    }, [])

    const integrations = [
        {
            title: "Google Classroom",
            description: "Import assignments, announcements, and due dates.",
            icon: GraduationCap,
            color: "text-green-500",
            bg: "bg-green-500/10",
            status: "Not Connected",
            action: "Connect",
        },
        {
            title: "Gmail",
            description: "Summarize emails from professors and catch up.",
            icon: Mail,
            color: "text-red-500",
            bg: "bg-red-500/10",
            status: "Not Connected",
            action: "Connect",
            connected: false,
        },
        {
            title: "Google Calendar",
            description: "Sync class schedules, exam dates, and study plans.",
            icon: Calendar,
            color: "text-blue-500",
            bg: "bg-blue-500/10",
            status: "Not Connected",
            action: "Sync Now",
            highlightAction: true,
        },
        {
            title: "AIMS",
            description: "Track academic transcripts, grades, and course credits.",
            icon: ClipboardList,
            color: "text-purple-500",
            bg: "bg-purple-500/10",
            status: "Not Connected",
            action: "Connect",
        },
        {
            title: "Personal Info",
            description: "Manage your student ID details, contact info, and preferences.",
            icon: User,
            color: "text-orange-500",
            bg: "bg-orange-500/10",
            status: "Active",
            action: "View",
            connected: true,
        },
    ]

    useEffect(() => {
        if (user && session) {
            fetchIntegrations()
        }
    }, [user, session])

    const fetchIntegrations = async () => {
        try {
            const res = await fetch(`${API_URL}/user/integrations`, {
                headers: {
                    "Authorization": `Bearer ${session?.access_token}`
                }
            })
            if (res.ok) {
                const data = await res.json()
                setConnectedIntegrations(data.integrations || [])
            }
        } catch (e) {
            console.error("Failed to fetch integrations", e)
        }
    }

    useEffect(() => {
        const status = searchParams.get("status")
        const errorDetail = searchParams.get("error_detail")
        if (status === "success") {
            console.log("Integration successful")
            window.history.replaceState(null, "", "/dashboard/integrations")
            if (user && session) {
                fetchIntegrations()
                // Also kick off a Gmail sync now that fresh tokens are stored
                fetch(`${API_URL}/gmail/sync?days_back=4`, {
                    method: "POST",
                    headers: { "Authorization": `Bearer ${session.access_token}` }
                }).then(() => fetchIntegrations()).catch(e => console.error("Gmail auto-sync after OAuth:", e))
            }
        } else if (status === "error") {
            const msg = errorDetail ? decodeURIComponent(errorDetail) : "Unknown error"
            console.error("Integration failed:", msg)
            alert(`Integration failed: ${msg}`)
            window.history.replaceState(null, "", "/dashboard/integrations")
        }
    }, [searchParams, user, session])

    const isConnected = (providerName: string) => {
        const dbName = providerName.toLowerCase().replace(" ", "_")
        return connectedIntegrations.some(i => i.provider === dbName)
    }

    const handleConnect = async (appName: string) => {
        const apiUrl = API_URL;

        if (appName === "Google Classroom") {
            if (!user) {
                console.error("User not found")
                return
            }
            if (isConnected("Google Classroom")) {
                // Already connected — resync using stored tokens, no OAuth needed
                try {
                    const res = await fetch(`${apiUrl}/classroom/resync`, {
                        method: "POST",
                        headers: { "Authorization": `Bearer ${session?.access_token}` }
                    })
                    if (res.ok) {
                        fetchIntegrations()
                    } else {
                        const err = await res.json().catch(() => ({}))
                        alert(`Resync failed: ${err.detail || "Unknown error"}`)
                    }
                } catch (e) {
                    console.error("Classroom resync error:", e)
                }
            } else {
                // First-time connect — go through OAuth
                window.location.href = `${apiUrl}/auth/google-classroom/authorize?user_id=${user.id}&callback_url=${encodeURIComponent(window.location.origin)}`
            }
        } else if (appName === "Google Calendar") {
            if (!user) {
                console.error("User not found")
                return
            }
            window.location.href = `${apiUrl}/auth/google-calendar/authorize?user_id=${user.id}&callback_url=${encodeURIComponent(window.location.origin)}`
        } else if (appName === "AIMS") {
            setIsAimsModalOpen(true)
        } else if (appName === "Gmail") {
            if (!user) return
            // Try to refresh the existing token first (no OAuth redirect needed)
            const alreadyConnected = isConnected("Google Classroom")
            if (!alreadyConnected) {
                alert("Please connect Google Classroom first — Gmail uses the same Google account.")
                return
            }
            try {
                const res = await fetch(`${apiUrl}/gmail/reconnect`, {
                    method: "POST",
                    headers: { "Authorization": `Bearer ${session?.access_token}` }
                })
                const data = await res.json().catch(() => ({}))
                if (res.ok && data.status === "reconnected") {
                    // Token refreshed — now kick off the sync
                    await fetch(`${apiUrl}/gmail/sync?days_back=4`, {
                        method: "POST",
                        headers: { "Authorization": `Bearer ${session?.access_token}` }
                    })
                    fetchIntegrations()
                } else if (data.status === "needs_oauth") {
                    // Refresh token is gone — must re-authorize via Google OAuth
                    window.location.href = `${apiUrl}/auth/google-classroom/authorize?user_id=${user.id}&callback_url=${encodeURIComponent(window.location.origin)}`
                } else {
                    console.error("Gmail reconnect failed:", data)
                    alert(`Gmail reconnect failed: ${data.detail || data.message || "Unknown error"}`)
                }
            } catch (e) {
                console.error("Gmail reconnect error:", e)
            }
        }
    }

    const handleLogout = async () => {
        await signOut()
    }

    const userName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || "Student"

    return (
        <div className="space-y-8">
            {/* Top Bar */}
            <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">Integrations Hub</h2>
                <div className="flex items-center gap-4">
                    <div className="relative w-64">
                        <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
                        <Input placeholder="Search integrations..." className="pl-9 bg-slate-900 border-slate-800" />
                    </div>
                    <Button variant="ghost" size="icon" className="text-slate-400 hover:text-white">
                        <Bell className="h-5 w-5" />
                    </Button>
                    <Button
                        variant="outline"
                        className="border-red-900/50 text-red-500 hover:bg-red-950 hover:text-red-400"
                        onClick={handleLogout}
                    >
                        Logout
                    </Button>
                    <Button className="bg-blue-600 hover:bg-blue-700">Upgrade Plan</Button>
                </div>
            </div>

            {/* Hero Section */}
            <div className="space-y-2">
                <h1 className="text-3xl font-bold">Good evening, {userName}</h1>
                <p className="text-slate-400 max-w-2xl">
                    Connect your accounts to let the AI organize your academic life, sync your deadlines, and summarize your emails.
                </p>
            </div>

            {/* Filters */}
            <div className="border-b border-slate-800">
                <div className="flex gap-6">
                    <button className="pb-3 border-b-2 border-blue-600 text-blue-500 font-medium text-sm">All Apps</button>
                    <button className="pb-3 border-b-2 border-transparent text-slate-400 hover:text-slate-300 font-medium text-sm transition-colors">Productivity</button>
                    <button className="pb-3 border-b-2 border-transparent text-slate-400 hover:text-slate-300 font-medium text-sm transition-colors">Communication</button>
                    <button className="pb-3 border-b-2 border-transparent text-slate-400 hover:text-slate-300 font-medium text-sm transition-colors">Utilities</button>
                </div>
            </div>

            {/* Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
                {integrations.map((item) => {
                    const connected = isConnected(item.title)
                    return (
                        <Card key={item.title} className="bg-slate-900/50 border-slate-800 hover:border-slate-700 transition-all">
                            <CardHeader>
                                <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-4 ${item.bg}`}>
                                    <item.icon className={`h-6 w-6 ${item.color}`} />
                                </div>
                                <CardTitle className="text-lg">{item.title}</CardTitle>
                                <CardDescription className="pt-2">{item.description}</CardDescription>
                            </CardHeader>
                            <CardFooter className="flex items-center justify-between border-t border-slate-800/50 pt-4 mt-auto">
                                <div className="flex items-center gap-2">
                                    <div className={`h-2 w-2 rounded-full ${connected ? "bg-green-500" : "bg-slate-600"}`} />
                                    <span className={`text-xs font-medium ${connected ? "text-green-500" : "text-slate-500"}`}>
                                        {(() => {
                                            if (!connected) return "Not Connected"
                                            if (item.title === "AIMS" || item.title === "Google Classroom") {
                                                const dbName = item.title.toLowerCase().replace(" ", "_")
                                                const integration = connectedIntegrations.find(i => i.provider === dbName)
                                                if (integration?.last_synced_at) {
                                                    const date = new Date(integration.last_synced_at)
                                                    return `Synced: ${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`
                                                }
                                            }
                                            return "Active"
                                        })()}
                                    </span>
                                </div>
                                <Button
                                    variant={item.highlightAction ? "default" : "outline"}
                                    className={item.highlightAction ? "bg-blue-600 hover:bg-blue-700" : "border-slate-700 hover:bg-slate-800 hover:text-white"}
                                    size="sm"
                                    onClick={() => handleConnect(item.title)}
                                    disabled={connected && item.title !== "AIMS" && item.title !== "Google Classroom" && item.title !== "Gmail"}
                                >
                                    {connected
                                        ? (item.title === "AIMS" || item.title === "Google Classroom" ? "Resync" : item.title === "Gmail" ? "Reconnect" : "Connected")
                                        : item.action}
                                </Button>
                            </CardFooter>
                        </Card>
                    )
                })}
            </div>

            <AimsConnectModal
                open={isAimsModalOpen}
                onOpenChange={setIsAimsModalOpen}
                onSuccess={fetchIntegrations}
            />
        </div >
    )
}
