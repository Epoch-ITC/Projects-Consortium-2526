"use client"

import { Send, Bot, Paperclip, Loader2, X } from "lucide-react"
import { Button } from "@/components/ui/Button"
import { useState, useRef, useEffect } from "react"
import { useAuth } from "@/context/AuthContext"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useParams, useRouter } from "next/navigation"
import { API_URL } from "@/lib/utils"

interface Message {
    id: string
    role: 'user' | 'ai'
    content: string
    created_at?: string
    timestamp?: string
}

export function ChatArea() {
    const { session, user } = useAuth()

    // Derive user initials from name or email
    const userInitials = (() => {
        const name = user?.user_metadata?.full_name || user?.user_metadata?.name
        if (name) {
            return name.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)
        }
        const email = user?.email
        if (email) {
            return email.slice(0, 2).toUpperCase()
        }
        return 'U'
    })()
    const params = useParams()
    const router = useRouter()
    const chatId = params?.chatId?.[0]

    const [messages, setMessages] = useState<Message[]>([])
    const [inputValue, setInputValue] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const [isFetchingHistory, setIsFetchingHistory] = useState(false)
    const [attachedFile, setAttachedFile] = useState<File | null>(null)

    const messagesEndRef = useRef<HTMLDivElement>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages, isLoading])

    // Fetch history when chatId changes
    useEffect(() => {
        if (!chatId) {
            setMessages([
                {
                    id: 'welcome',
                    role: 'ai',
                    content: "Hello! I'm here to help you with your studies. Start a new conversation or select one from the history.",
                    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                }
            ])
            return
        }

        const fetchHistory = async () => {
            setIsFetchingHistory(true)
            try {
                const res = await fetch(`${API_URL}/chats/${chatId}/messages`, {
                    headers: {
                        "Authorization": `Bearer ${session?.access_token}`
                    }
                })
                const data = await res.json()
                if (data.messages) {
                    setMessages(data.messages.map((m: any) => ({
                        ...m,
                        timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    })))
                }
            } catch (e) {
                console.error("Failed to fetch history", e)
            } finally {
                setIsFetchingHistory(false)
            }
        }

        if (session?.access_token) {
            fetchHistory()
        }
    }, [chatId, session?.access_token])

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (file) {
            setAttachedFile(file)
        }
        // Reset input so same file can be selected again
        if (fileInputRef.current) fileInputRef.current.value = ""
    }

    const removeAttachedFile = () => {
        setAttachedFile(null)
    }

    const handleSendMessage = async () => {
        if ((!inputValue.trim() && !attachedFile) || isLoading) return

        const userMessageContent = inputValue
        const tempId = Date.now().toString()

        const userMessage: Message = {
            id: tempId,
            role: 'user',
            content: userMessageContent,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }

        setMessages(prev => [...prev, userMessage])
        setInputValue("")
        setIsLoading(true)

        try {
            let activeChatId = chatId

            // Auto-create chat if it doesn't exist
            if (!activeChatId) {
                const createRes = await fetch(`${API_URL}/chats`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${session?.access_token}`
                    },
                    body: JSON.stringify({ title: userMessageContent.slice(0, 30) || "New Chat" })
                })
                const createData = await createRes.json()
                if (createData.chat) {
                    activeChatId = createData.chat.id
                    router.push(`/dashboard/chat/${activeChatId}`)
                } else {
                    throw new Error("Failed to create chat")
                }
            }

            // Upload file first if attached
            if (attachedFile) {
                const formData = new FormData()
                formData.append("file", attachedFile)

                const uploadRes = await fetch(`${API_URL}/chats/${activeChatId}/upload`, {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${session?.access_token}`
                    },
                    body: formData
                })

                if (uploadRes.ok) {
                    const uploadData = await uploadRes.json()
                    // Add file message to UI
                    const fileMsg: Message = {
                        id: (Date.now() + 0.5).toString(),
                        role: 'user',
                        content: uploadData.message,
                        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    }
                    setMessages(prev => [...prev, fileMsg])
                } else {
                    const errData = await uploadRes.json().catch(() => ({}))
                    console.error("Upload failed:", errData.detail || "Unknown error")
                }
                setAttachedFile(null)
            }

            // Send chat message (even if empty, skip if no text)
            if (userMessageContent.trim()) {
                const response = await fetch(`${API_URL}/chat`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${session?.access_token}`
                    },
                    body: JSON.stringify({
                        message: userMessageContent,
                        chat_id: activeChatId
                    }),
                })

                if (!response.ok) {
                    throw new Error("Failed to fetch response")
                }

                const data = await response.json()

                const aiMessage: Message = {
                    id: (Date.now() + 1).toString(),
                    role: 'ai',
                    content: data.response,
                    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                }

                setMessages(prev => [...prev, aiMessage])
            }
        } catch (error) {
            console.error("Error sending message:", error)
        } finally {
            setIsLoading(false)
        }
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSendMessage()
        }
    }

    return (
        <div className="flex-1 flex flex-col h-full bg-slate-950">
            {/* Header */}
            <div className="h-14 border-b border-slate-800 flex items-center justify-between px-6 bg-slate-950/50 backdrop-blur-sm">
                <div>
                    <h2 className="font-semibold text-white">
                        {chatId ? "Chat Session" : "New Conversation"}
                    </h2>
                    <div className="flex items-center gap-1.5">
                        <div className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-xs text-slate-400">AI Online</span>
                    </div>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-8">
                {isFetchingHistory ? (
                    <div className="flex justify-center items-center h-full">
                        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
                    </div>
                ) : (
                    <>
                        {messages.map((message) => (
                            <div key={message.id} className={`flex gap-4 max-w-4xl ${message.role === 'user' ? 'flex-row-reverse ml-auto' : ''}`}>
                                <div className={`h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${message.role === 'ai' ? 'bg-blue-600' : 'bg-blue-200 text-blue-800 font-bold text-xs'}`}>
                                    {message.role === 'ai' ? <Bot className="h-5 w-5 text-white" /> : userInitials}
                                </div>
                                <div className="flex-1 space-y-2">
                                    <div className={`flex items-center gap-2 ${message.role === 'user' ? 'justify-end' : ''}`}>
                                        {message.role === 'ai' && <span className="font-semibold text-sm">Student AI</span>}
                                        {message.role === 'user' && <span className="text-xs text-slate-500">{message.timestamp}</span>}
                                        {message.role === 'user' && <span className="font-semibold text-sm">You</span>}
                                        {message.role === 'ai' && <span className="text-xs text-slate-500">{message.timestamp}</span>}
                                    </div>
                                    <div className={`${message.role === 'ai' ? 'bg-slate-900 border border-slate-800 text-slate-300' : 'bg-blue-600 text-white'} p-4 rounded-xl ${message.role === 'user' ? 'rounded-tr-sm' : ''} text-sm`}>
                                        {message.role === 'ai' ? (
                                            <div className="prose prose-invert prose-sm max-w-none [&>p]:mb-4 [&>p:last-child]:mb-0 [&>ul]:list-disc [&>ul]:pl-4 [&>ol]:list-decimal [&>ol]:pl-4 [&>a]:text-blue-400 [&>a]:underline [&>a]:break-all">
                                                <ReactMarkdown
                                                    remarkPlugins={[remarkGfm]}
                                                    components={{
                                                        a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />
                                                    }}
                                                >
                                                    {message.content}
                                                </ReactMarkdown>
                                            </div>
                                        ) : (
                                            <div className="whitespace-pre-wrap">
                                                <ReactMarkdown
                                                    remarkPlugins={[remarkGfm]}
                                                    components={{
                                                        a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />
                                                    }}
                                                >
                                                    {message.content}
                                                </ReactMarkdown>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                        {isLoading && (
                            <div className="flex gap-4 max-w-4xl">
                                <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0 mt-1">
                                    <Bot className="h-5 w-5 text-white" />
                                </div>
                                <div className="flex-1 space-y-2">
                                    <div className="flex items-center gap-2">
                                        <span className="font-semibold text-sm">Student AI</span>
                                    </div>
                                    <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl w-fit">
                                        <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </>
                )}
            </div>

            {/* Input Area */}
            <div className="p-4 bg-slate-950">
                <div className="max-w-4xl mx-auto bg-slate-900/50 rounded-xl border border-slate-800 p-2 focus-within:ring-2 focus-within:ring-blue-600/50 transition-all">
                    {/* File preview */}
                    {attachedFile && (
                        <div className="flex items-center gap-2 px-3 py-2 mb-1 bg-slate-800/50 rounded-lg mx-1">
                            <Paperclip className="h-3.5 w-3.5 text-blue-400 flex-shrink-0" />
                            <span className="text-xs text-slate-300 truncate flex-1">{attachedFile.name}</span>
                            <span className="text-[10px] text-slate-500">{(attachedFile.size / 1024).toFixed(1)} KB</span>
                            <button
                                onClick={removeAttachedFile}
                                className="p-0.5 rounded hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
                            >
                                <X className="h-3.5 w-3.5" />
                            </button>
                        </div>
                    )}
                    {/* Input row */}
                    <div className="flex items-center gap-2 px-2 pb-2">
                        <input
                            ref={fileInputRef}
                            type="file"
                            className="hidden"
                            accept=".txt,.md,.csv,.py,.js,.ts,.json,.log,.xml,.html,.css"
                            onChange={handleFileSelect}
                        />
                        <Button
                            variant="ghost"
                            size="icon"
                            className={`h-8 w-8 rounded-full hover:bg-slate-800 ${attachedFile ? 'text-blue-400' : 'text-slate-400 hover:text-white'}`}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <Paperclip className="h-4 w-4" />
                        </Button>
                        <input
                            type="text"
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ask anything about your studies..."
                            className="flex-1 bg-transparent border-none focus:outline-none text-white px-2 py-3 placeholder-slate-500"
                        />
                    </div>
                    <div className="flex items-center justify-between px-2 pt-2 border-t border-slate-800/50">
                        <span className="text-[10px] text-slate-500">Use Shift + Enter for new line</span>
                        <Button
                            size="icon"
                            className="h-8 w-8 bg-blue-600 hover:bg-blue-700 rounded-lg"
                            onClick={handleSendMessage}
                            disabled={isLoading || (!inputValue.trim() && !attachedFile)}
                        >
                            <Send className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
                <p className="text-center text-xs text-slate-600 mt-2">
                    Student AI can make mistakes. Consider checking important information.
                </p>
            </div>
        </div>
    )
}
