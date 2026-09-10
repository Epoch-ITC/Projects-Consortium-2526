"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/Dialog"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Label } from "@/components/ui/Label"
import { Loader2, CheckCircle2, AlertCircle } from "lucide-react"
import { useAuth } from "@/context/AuthContext"
import { API_URL } from "@/lib/utils"

interface AimsConnectModalProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    onSuccess?: () => void
}

export function AimsConnectModal({ open, onOpenChange, onSuccess }: AimsConnectModalProps) {
    const { session } = useAuth()
    const [username, setUsername] = useState("")
    const [password, setPassword] = useState("")
    const [loading, setLoading] = useState(false)
    const [status, setStatus] = useState<"idle" | "success" | "error">("idle")
    const [errorMsg, setErrorMsg] = useState("")

    const handleSync = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        setStatus("idle")
        setErrorMsg("")

        try {
            const res = await fetch(`${API_URL}/aims/sync`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${session?.access_token}`
                },
                body: JSON.stringify({ username, password })
            })

            if (!res.ok) {
                const data = await res.json()
                throw new Error(data.detail || "Sync Failed")
            }

            setStatus("success")
            // Wait a moment then close
            setTimeout(() => {
                onOpenChange(false)
                if (onSuccess) onSuccess()
            }, 1500)

        } catch (e: any) {
            setStatus("error")
            setErrorMsg(e.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px] bg-slate-900 text-white border-slate-800">
                <DialogHeader>
                    <DialogTitle>Connect AIMS Portal</DialogTitle>
                    <DialogDescription className="text-slate-400">
                        Enter your AIMS credentials to sync your grades. We verify them once and fetch your data. Your password is NOT stored.
                    </DialogDescription>
                </DialogHeader>

                {status === "success" ? (
                    <div className="flex flex-col items-center justify-center py-6 space-y-4">
                        <div className="h-12 w-12 rounded-full bg-green-500/20 flex items-center justify-center">
                            <CheckCircle2 className="h-6 w-6 text-green-500" />
                        </div>
                        <p className="font-medium text-green-500">Grades Synced Successfully!</p>
                    </div>
                ) : (
                    <form onSubmit={handleSync} className="space-y-4 pt-4">
                        <div className="space-y-2">
                            <Label htmlFor="username">Username (Roll No)</Label>
                            <Input
                                id="username"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="e.g. AI21BTECH11001"
                                className="bg-slate-950 border-slate-800 focus:border-purple-500"
                                required
                                disabled={loading}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="password">Password</Label>
                            <Input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                className="bg-slate-950 border-slate-800 focus:border-purple-500"
                                required
                                disabled={loading}
                            />
                        </div>

                        {status === "error" && (
                            <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 text-red-500 text-sm">
                                <AlertCircle className="h-4 w-4" />
                                <p>{errorMsg}</p>
                            </div>
                        )}

                        <Button
                            type="submit"
                            className="w-full bg-purple-600 hover:bg-purple-700 disabled:opacity-50"
                            disabled={loading}
                        >
                            {loading ? (
                                <>
                                    <Loader2 className="mr-2 h-shrink-0 min-w-4 w-4 animate-spin" />
                                    Syncing...
                                </>
                            ) : (
                                "Sync Grades"
                            )}
                        </Button>
                        {loading && (
                            <p className="text-xs text-center text-slate-400 mt-2">
                                Please wait... this may take around 10–15 seconds.
                            </p>
                        )}
                    </form>
                )}
            </DialogContent>
        </Dialog>
    )
}
