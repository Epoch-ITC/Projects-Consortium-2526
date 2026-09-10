"use client"

import { useState, useEffect } from "react"
import { API_URL } from "@/lib/utils"
import { Key, Brain, Eye, EyeOff, Save, Loader2, CheckCircle, AlertCircle, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { useAuth } from "@/context/AuthContext"

const MODEL_OPTIONS = [
    { value: "gemini-2.0-flash", label: "Gemini 2.0 Flash" },
    { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
    { value: "gemini-2.5-pro", label: "Gemini 2.5 Pro" },
    { value: "gemini-2.5-flash-lite", label: "Gemini 2.5 Flash Lite" },
    { value: "gemini-3-pro", label: "Gemini 3 Pro" },
    { value: "gemini-3-flash", label: "Gemini 3 Flash" },
]

export default function SettingsPage() {
    const { session } = useAuth()

    const [apiKey, setApiKey] = useState("")
    const [showApiKey, setShowApiKey] = useState(false)
    const [plannerModel, setPlannerModel] = useState("gemini-2.5-flash")
    const [presenterModel, setPresenterModel] = useState("gemini-2.5-flash")
    const [hasExistingKey, setHasExistingKey] = useState(false)
    const [maskedKey, setMaskedKey] = useState("")

    const [hfToken, setHfToken] = useState("")
    const [showHfToken, setShowHfToken] = useState(false)
    const [hasExistingHfToken, setHasExistingHfToken] = useState(false)
    const [maskedHfToken, setMaskedHfToken] = useState("")

    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)
    const [saveStatus, setSaveStatus] = useState<"idle" | "success" | "error">("idle")
    const [errorMessage, setErrorMessage] = useState("")

    useEffect(() => {
        document.title = "Settings - Student Helper"
    }, [])

    useEffect(() => {
        if (session?.access_token) {
            fetchSettings()
        }
    }, [session?.access_token])

    const fetchSettings = async () => {
        try {
            const res = await fetch(`${API_URL}/user/settings`, {
                headers: { "Authorization": `Bearer ${session?.access_token}` }
            })
            if (res.ok) {
                const data = await res.json()
                const s = data.settings
                setHasExistingKey(s.has_api_key)
                setMaskedKey(s.gemini_api_key_masked)
                setPlannerModel(s.planner_model)
                setPresenterModel(s.presenter_model)
                setHasExistingHfToken(s.has_hf_token)
                setMaskedHfToken(s.hf_token_masked)
            }
        } catch (e) {
            console.error("Failed to fetch settings", e)
        } finally {
            setIsLoading(false)
        }
    }

    const handleSave = async () => {
        setIsSaving(true)
        setSaveStatus("idle")
        setErrorMessage("")
        try {
            const body: any = {
                planner_model: plannerModel,
                presenter_model: presenterModel,
            }
            // Only send API key if user typed a new one
            if (apiKey.trim()) {
                body.gemini_api_key = apiKey.trim()
            }
            // Only send HF token if user typed a new one
            if (hfToken.trim()) {
                body.huggingface_token = hfToken.trim()
            }

            const res = await fetch(`${API_URL}/user/settings`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${session?.access_token}`
                },
                body: JSON.stringify(body)
            })

            if (res.ok) {
                setSaveStatus("success")
                if (apiKey.trim()) {
                    setHasExistingKey(true)
                    setMaskedKey(`...${apiKey.trim().slice(-4)}`)
                    setApiKey("")
                }
                if (hfToken.trim()) {
                    setHasExistingHfToken(true)
                    setMaskedHfToken(`...${hfToken.trim().slice(-4)}`)
                    setHfToken("")
                }
                setTimeout(() => setSaveStatus("idle"), 3000)
            } else {
                const err = await res.json().catch(() => ({}))
                setSaveStatus("error")
                setErrorMessage(err.detail || "Failed to save")
            }
        } catch (e) {
            setSaveStatus("error")
            setErrorMessage("Network error")
        } finally {
            setIsSaving(false)
        }
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-full">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
        )
    }

    return (
        <div className="max-w-2xl mx-auto py-10 px-6 space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-white">Settings</h1>
                <p className="text-slate-400 text-sm mt-1">
                    Configure your AI assistant&apos;s behavior and API access.
                </p>
            </div>

            {/* API Key Section */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-amber-500/10 rounded-lg">
                        <Key className="h-5 w-5 text-amber-400" />
                    </div>
                    <div>
                        <h2 className="font-semibold text-white">Gemini API Key</h2>
                        <p className="text-xs text-slate-400">
                            Required to use the AI chat. Get one free from{" "}
                            <a
                                href="https://aistudio.google.com/apikey"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-400 hover:underline"
                            >
                                Google AI Studio
                            </a>
                        </p>
                    </div>
                </div>

                {hasExistingKey && (
                    <div className="flex items-center gap-2 px-3 py-2 bg-green-500/10 border border-green-500/20 rounded-lg">
                        <CheckCircle className="h-4 w-4 text-green-400 flex-shrink-0" />
                        <span className="text-sm text-green-300">
                            API key configured <span className="text-slate-500">({maskedKey})</span>
                        </span>
                    </div>
                )}

                <div className="relative">
                    <input
                        type={showApiKey ? "text" : "password"}
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        placeholder={hasExistingKey ? "Enter new key to replace..." : "AIza..."}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 pr-12 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-600/50 focus:border-blue-600"
                    />
                    <button
                        type="button"
                        onClick={() => setShowApiKey(!showApiKey)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
                    >
                        {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                </div>

                {!hasExistingKey && (
                    <div className="flex items-start gap-2 px-3 py-2 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                        <AlertCircle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
                        <span className="text-xs text-amber-300">
                            You need to add an API key before you can use the chat.
                        </span>
                    </div>
                )}
            </div>

            {/* Hugging Face Token Section */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-yellow-500/10 rounded-lg">
                        <Key className="h-5 w-5 text-yellow-400" />
                    </div>
                    <div>
                        <h2 className="font-semibold text-white">Hugging Face Token</h2>
                        <p className="text-xs text-slate-400">
                            Required for AI-powered search over your course materials. Get one from{" "}
                            <a
                                href="https://huggingface.co/settings/tokens"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-400 hover:underline"
                            >
                                Hugging Face Settings
                            </a>
                        </p>
                    </div>
                </div>

                {hasExistingHfToken && (
                    <div className="flex items-center gap-2 px-3 py-2 bg-green-500/10 border border-green-500/20 rounded-lg">
                        <CheckCircle className="h-4 w-4 text-green-400 flex-shrink-0" />
                        <span className="text-sm text-green-300">
                            HF token configured <span className="text-slate-500">({maskedHfToken})</span>
                        </span>
                    </div>
                )}

                <div className="relative">
                    <input
                        type={showHfToken ? "text" : "password"}
                        value={hfToken}
                        onChange={(e) => setHfToken(e.target.value)}
                        placeholder={hasExistingHfToken ? "Enter new token to replace..." : "hf_..."}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 pr-12 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-600/50 focus:border-blue-600"
                    />
                    <button
                        type="button"
                        onClick={() => setShowHfToken(!showHfToken)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
                    >
                        {showHfToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                </div>

                {!hasExistingHfToken && (
                    <div className="flex items-start gap-2 px-3 py-2 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                        <AlertCircle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
                        <span className="text-xs text-amber-300">
                            You need to add a Hugging Face token for course material search to work.
                        </span>
                    </div>
                )}
            </div>

            {/* Model Selection Section */}
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-6">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-purple-500/10 rounded-lg">
                        <Sparkles className="h-5 w-5 text-purple-400" />
                    </div>
                    <div>
                        <h2 className="font-semibold text-white">Model Selection</h2>
                        <p className="text-xs text-slate-400">
                            Choose which Gemini models to use for planning and presenting.
                        </p>
                    </div>
                </div>

                {/* Planner Model */}
                <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                        <Brain className="h-4 w-4 text-blue-400" />
                        Planner Model
                    </label>
                    <p className="text-xs text-slate-500 ml-6">
                        Decides which tools to call and gathers information.
                    </p>
                    <select
                        value={plannerModel}
                        onChange={(e) => setPlannerModel(e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-600/50 appearance-none cursor-pointer"
                    >
                        {MODEL_OPTIONS.map(m => (
                            <option key={m.value} value={m.value}>{m.label}</option>
                        ))}
                    </select>
                </div>

                {/* Presenter Model */}
                <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
                        <Brain className="h-4 w-4 text-purple-400" />
                        Presenter Model
                    </label>
                    <p className="text-xs text-slate-500 ml-6">
                        Writes the final response you see in the chat.
                    </p>
                    <select
                        value={presenterModel}
                        onChange={(e) => setPresenterModel(e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-600/50 appearance-none cursor-pointer"
                    >
                        {MODEL_OPTIONS.map(m => (
                            <option key={m.value} value={m.value}>{m.label}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Save Button */}
            <div className="flex items-center gap-4">
                <Button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="bg-blue-600 hover:bg-blue-700 px-8"
                >
                    {isSaving ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    ) : (
                        <Save className="h-4 w-4 mr-2" />
                    )}
                    Save Settings
                </Button>

                {saveStatus === "success" && (
                    <div className="flex items-center gap-2 text-green-400 text-sm animate-in fade-in">
                        <CheckCircle className="h-4 w-4" />
                        Settings saved!
                    </div>
                )}
                {saveStatus === "error" && (
                    <div className="flex items-center gap-2 text-red-400 text-sm">
                        <AlertCircle className="h-4 w-4" />
                        {errorMessage}
                    </div>
                )}
            </div>
        </div>
    )
}
