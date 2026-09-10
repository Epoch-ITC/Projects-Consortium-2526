"use client"

import Link from "next/link"
import { MessageSquare, Plus, Loader2, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { useEffect, useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { useAuth } from "@/context/AuthContext"
import { API_URL } from "@/lib/utils"

interface ChatSession {
    id: string
    title: string
    created_at: string
}

export function ChatHistory() {
    const { session } = useAuth()
    const router = useRouter()
    const params = useParams()
    const currentChatId = params?.chatId?.[0]

    const [chats, setChats] = useState<ChatSession[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [isCreating, setIsCreating] = useState(false)
    const [deletingId, setDeletingId] = useState<string | null>(null)

    useEffect(() => {
        if (session?.access_token) {
            fetchChats()
        }
    }, [session?.access_token])

    const fetchChats = async () => {
        setIsLoading(true)
        try {
            const res = await fetch(`${API_URL}/chats`, {
                headers: {
                    "Authorization": `Bearer ${session?.access_token}`
                }
            })
            const data = await res.json()
            if (data.chats) {
                setChats(data.chats)
            }
        } catch (e) {
            console.error("Failed to fetch chats", e)
        } finally {
            setIsLoading(false)
        }
    }

    const handleNewChat = async () => {
        setIsCreating(true)
        try {
            const res = await fetch(`${API_URL}/chats`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${session?.access_token}`
                },
                body: JSON.stringify({ title: "New Chat" })
            })
            const data = await res.json()
            if (data.chat) {
                setChats([data.chat, ...chats])
                router.push(`/dashboard/chat/${data.chat.id}`)
            }
        } catch (e) {
            console.error("Failed to create chat", e)
        } finally {
            setIsCreating(false)
        }
    }

    const handleDeleteChat = async (e: React.MouseEvent, chatId: string) => {
        e.preventDefault()
        e.stopPropagation()

        setDeletingId(chatId)
        try {
            const res = await fetch(`${API_URL}/chats/${chatId}`, {
                method: "DELETE",
                headers: {
                    "Authorization": `Bearer ${session?.access_token}`
                }
            })

            if (res.ok) {
                // Remove from local state
                setChats(prev => prev.filter(c => c.id !== chatId))

                // Navigate away if we deleted the active chat
                if (currentChatId === chatId) {
                    router.push("/dashboard/chat")
                }
            }
        } catch (e) {
            console.error("Failed to delete chat", e)
        } finally {
            setDeletingId(null)
        }
    }

    return (
        <div className="w-80 flex-shrink-0 border-r border-slate-800 bg-slate-950 flex flex-col h-full">
            <div className="p-4">
                <Button
                    onClick={handleNewChat}
                    disabled={isCreating}
                    className="w-full justify-start gap-2 bg-blue-600 hover:bg-blue-700"
                >
                    {isCreating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                    New Chat
                </Button>
            </div>

            <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">
                {isLoading && (
                    <div className="flex justify-center py-4">
                        <Loader2 className="h-5 w-5 animate-spin text-slate-500" />
                    </div>
                )}

                {!isLoading && chats.length === 0 && (
                    <div className="text-center py-8 text-slate-500 text-sm">
                        No chats yet. Start one!
                    </div>
                )}

                {chats.map(chat => {
                    const isActive = currentChatId === chat.id
                    const isDeleting = deletingId === chat.id
                    return (
                        <Link
                            key={chat.id}
                            href={`/dashboard/chat/${chat.id}`}
                            className={`group w-full flex items-center gap-3 px-3 py-3 rounded-lg text-sm transition-colors text-left ${isActive
                                ? "bg-slate-800 text-white"
                                : "text-slate-400 hover:bg-slate-900 hover:text-white"
                                } ${isDeleting ? "opacity-50 pointer-events-none" : ""}`}
                        >
                            <MessageSquare className={`h-4 w-4 flex-shrink-0 ${isActive ? "text-blue-400" : "text-slate-500"}`} />
                            <span className="truncate flex-1">{chat.title || "Untitled Chat"}</span>
                            <button
                                onClick={(e) => handleDeleteChat(e, chat.id)}
                                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-red-500/20 text-slate-500 hover:text-red-400 flex-shrink-0"
                                title="Delete chat"
                            >
                                {isDeleting ? (
                                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                ) : (
                                    <Trash2 className="h-3.5 w-3.5" />
                                )}
                            </button>
                        </Link>
                    )
                })}
            </div>
        </div>
    )
}
