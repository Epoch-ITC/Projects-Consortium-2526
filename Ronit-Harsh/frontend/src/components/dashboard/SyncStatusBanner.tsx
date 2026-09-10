"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@/context/AuthContext"
import { createClient } from "@/utils/supabase/client"
import { Loader2, X } from "lucide-react"
import { API_URL } from "@/lib/utils"

// Create Supabase client once at module level
const supabase = createClient()

export function SyncStatusBanner() {
    const { user, session } = useAuth()
    const [status, setStatus] = useState<string>("idle")
    const [progress, setProgress] = useState<number>(0)
    const [visible, setVisible] = useState(false)
    const [cancelling, setCancelling] = useState(false)

    useEffect(() => {
        if (!user) return

        const checkStatus = async () => {
            const { data, error } = await supabase
                .from("user_integrations")
                .select("sync_status, sync_progress, last_synced_at")
                .eq("user_id", user.id)
                .eq("provider", "google_classroom") // Focus on Classroom for now
                .single()

            if (data) {
                if (data.sync_status === 'in_progress') {
                    setStatus('in_progress')
                    setProgress(data.sync_progress || 0)
                    setVisible(true)
                } else if (data.sync_status === 'success') {
                    setStatus(prev => {
                        if (prev === 'in_progress') {
                            setProgress(100)
                            setTimeout(() => setVisible(false), 5000)
                        }
                        return prev === 'in_progress' ? 'success' : prev
                    })
                } else if (data.sync_status === 'cancelled' || data.sync_status === 'idle') {
                    if (status === 'in_progress') {
                        // Was syncing, now cancelled/idle — hide banner
                        setVisible(false)
                        setCancelling(false)
                    }
                } else if (data.sync_status === 'error') {
                    // Only show error if it happened recently (within last 5 minutes)
                    const lastSync = data.last_synced_at ? new Date(data.last_synced_at) : null
                    const now = new Date()
                    const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000)

                    if (lastSync && lastSync > fiveMinutesAgo) {
                        setStatus('error')
                        setVisible(true)
                    } else {
                        // Stale error, hide it
                        setVisible(false)
                    }
                }
            }
        }

        // Poll every 3 seconds
        const interval = setInterval(checkStatus, 3000)
        checkStatus() // Initial check

        return () => clearInterval(interval)
    }, [user])

    const handleCancel = async () => {
        setCancelling(true)
        try {
            const apiUrl = API_URL
            await fetch(`${apiUrl}/classroom/cancel-sync`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${session?.access_token}` }
            })
        } catch (e) {
            console.error("Failed to cancel sync:", e)
            setCancelling(false)
        }
    }

    if (!visible) return null

    return (
        <div className="bg-blue-900/50 border-b border-blue-800 px-6 py-3">
            <div className="flex items-center justify-between max-w-7xl mx-auto">
                <div className="flex items-center gap-3">
                    {status === 'in_progress' ? (
                        <Loader2 className="h-5 w-5 text-blue-400 animate-spin" />
                    ) : status === 'success' ? (
                        <div className="h-5 w-5 rounded-full bg-green-500 flex items-center justify-center">
                            <span className="text-white text-xs">✓</span>
                        </div>
                    ) : (
                        <div className="h-5 w-5 rounded-full bg-red-500 flex items-center justify-center">
                            <span className="text-white text-xs">!</span>
                        </div>
                    )}
                    <div>
                        <p className="text-sm font-medium text-blue-100">
                            {status === 'in_progress'
                                ? "Importing Classroom Data..."
                                : status === 'success'
                                    ? "Import Complete!"
                                    : "Import Failed"}
                        </p>
                        <p className="text-xs text-blue-300">
                            {status === 'in_progress'
                                ? "We're chunking your assignments and vectorizing content."
                                : status === 'success'
                                    ? "Your knowledge base is up to date."
                                    : "Please try reconnecting via the Integrations page."}
                        </p>
                    </div>
                </div>

                {status === 'in_progress' && (
                    <div className="flex items-center gap-4">
                        <div className="w-64">
                            <div className="flex justify-between text-xs text-blue-300 mb-1">
                                <span>Progress</span>
                                <span>{progress}%</span>
                            </div>
                            <div className="h-2 bg-blue-950 rounded-full overflow-hidden">
                                <div
                                    className="h-full bg-blue-500 transition-all duration-500 ease-out"
                                    style={{ width: `${progress}%` }}
                                />
                            </div>
                        </div>
                        <button
                            onClick={handleCancel}
                            disabled={cancelling}
                            className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-red-300 bg-red-500/10 border border-red-500/20 rounded-lg hover:bg-red-500/20 transition-colors disabled:opacity-50"
                        >
                            <X className="h-3 w-3" />
                            {cancelling ? "Cancelling..." : "Cancel"}
                        </button>
                    </div>
                )}
            </div>
        </div>
    )
}
