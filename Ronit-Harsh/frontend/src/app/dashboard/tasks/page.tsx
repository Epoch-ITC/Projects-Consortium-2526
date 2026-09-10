"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import { API_URL } from "@/lib/utils"
import { useAuth } from "@/context/AuthContext"
import { Card, CardContent } from "@/components/ui/Card"
import { Button } from "@/components/ui/Button"
import { Input } from "@/components/ui/Input"
import { Plus, CheckCircle2, Circle, Trash2, Calendar, Clock, Filter } from "lucide-react"

interface Todo {
    id: string
    title: string
    description: string | null
    due_at: string | null
    is_completed: boolean
    priority: string
    source: string
    gcal_event_id: string | null
    created_at: string
}

type FilterTab = "all" | "active" | "completed"

export default function TasksPage() {
    const { user, session } = useAuth()
    const [todos, setTodos] = useState<Todo[]>([])
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState<FilterTab>("all")
    const [showForm, setShowForm] = useState(false)
    const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null)
    const hasFetched = useRef(false)

    // Form state
    const [newTitle, setNewTitle] = useState("")
    const [newDueAt, setNewDueAt] = useState("")
    const [newPriority, setNewPriority] = useState("medium")
    const [newDescription, setNewDescription] = useState("")
    const [submitting, setSubmitting] = useState(false)

    useEffect(() => {
        document.title = "Tasks - Student Helper"
    }, [])

    const showToast = (message: string, type: "success" | "error" = "success") => {
        setToast({ message, type })
        setTimeout(() => setToast(null), 3000)
    }

    const fetchTodos = useCallback(async (force = false) => {
        if (!session?.access_token) {
            setLoading(false)
            return
        }
        // Skip if already fetched and not forced
        if (hasFetched.current && !force) {
            setLoading(false)
            return
        }
        try {
            setLoading(true)
            // Always fetch ALL todos — filtering is done client-side
            const res = await fetch(`${API_URL}/todos`, {
                headers: { Authorization: `Bearer ${session.access_token}` },
            })
            if (res.ok) {
                const data = await res.json()
                setTodos(data.todos || [])
                hasFetched.current = true
            }
        } catch (e) {
            console.error("Failed to fetch todos", e)
        } finally {
            setLoading(false)
        }
    }, [session?.access_token])

    useEffect(() => {
        if (user && session) fetchTodos()
    }, [user, session, fetchTodos])

    const handleCreate = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!newTitle.trim()) return

        try {
            setSubmitting(true)
            const body: any = {
                title: newTitle.trim(),
                priority: newPriority,
                source: "manual",
            }
            if (newDueAt) body.due_at = new Date(newDueAt).toISOString()
            if (newDescription.trim()) body.description = newDescription.trim()

            const res = await fetch(`${API_URL}/todos`, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${session?.access_token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(body),
            })
            if (res.ok) {
                showToast("Task added! ✅")
                setNewTitle("")
                setNewDueAt("")
                setNewPriority("medium")
                setNewDescription("")
                setShowForm(false)
                fetchTodos(true)  // Force refetch to get server-generated fields
            } else {
                showToast("Failed to create task", "error")
            }
        } catch (e) {
            console.error("Create todo failed", e)
            showToast("Failed to create task", "error")
        } finally {
            setSubmitting(false)
        }
    }

    const handleToggle = async (todo: Todo) => {
        try {
            const res = await fetch(`${API_URL}/todos/${todo.id}`, {
                method: "PUT",
                headers: {
                    Authorization: `Bearer ${session?.access_token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ is_completed: !todo.is_completed }),
            })
            if (res.ok) {
                setTodos((prev) =>
                    prev.map((t) => (t.id === todo.id ? { ...t, is_completed: !t.is_completed } : t))
                )
                showToast(todo.is_completed ? "Task reopened" : "Task completed! 🎉")
            }
        } catch (e) {
            console.error("Toggle failed", e)
        }
    }

    const handleDelete = async (todoId: string) => {
        try {
            const res = await fetch(`${API_URL}/todos/${todoId}`, {
                method: "DELETE",
                headers: { Authorization: `Bearer ${session?.access_token}` },
            })
            if (res.ok) {
                setTodos((prev) => prev.filter((t) => t.id !== todoId))
                showToast("Task deleted")
            }
        } catch (e) {
            console.error("Delete failed", e)
        }
    }

    const formatDue = (dateStr: string | null) => {
        if (!dateStr) return null
        const date = new Date(dateStr)
        const now = new Date()
        const diffMs = date.getTime() - now.getTime()
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
        const diffDays = Math.floor(diffHours / 24)

        const timeStr = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
        const dateFormatted = date.toLocaleDateString([], { month: "short", day: "numeric" })

        if (diffMs < 0) return { text: `Overdue · ${dateFormatted} ${timeStr}`, color: "text-red-400" }
        if (diffHours < 24) return { text: `Today · ${timeStr}`, color: "text-amber-400" }
        if (diffDays < 2) return { text: `Tomorrow · ${timeStr}`, color: "text-blue-400" }
        return { text: `${dateFormatted} · ${timeStr}`, color: "text-slate-400" }
    }

    const priorityConfig: Record<string, { dot: string; label: string }> = {
        high: { dot: "bg-red-500", label: "High" },
        medium: { dot: "bg-amber-500", label: "Medium" },
        low: { dot: "bg-green-500", label: "Low" },
    }

    const sourceLabel: Record<string, string> = {
        manual: "",
        chat: "🤖 from chat",
        classroom: "📚 from classroom",
    }

    const activeTodos = todos.filter((t) => !t.is_completed)
    const completedTodos = todos.filter((t) => t.is_completed)
    const filteredTodos = filter === "active" ? activeTodos : filter === "completed" ? completedTodos : todos

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="space-y-1">
                    <h1 className="text-3xl font-bold">Tasks</h1>
                    <p className="text-slate-400">
                        {activeTodos.length} active · {completedTodos.length} completed
                    </p>
                </div>
                <Button
                    onClick={() => setShowForm(!showForm)}
                    className="bg-blue-600 hover:bg-blue-700"
                >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Task
                </Button>
            </div>

            {/* Add Task Form */}
            {showForm && (
                <Card className="bg-slate-900/80 border-slate-700 border-2 border-dashed">
                    <CardContent className="pt-6">
                        <form onSubmit={handleCreate} className="space-y-4">
                            <div>
                                <Input
                                    placeholder="What do you need to do?"
                                    value={newTitle}
                                    onChange={(e) => setNewTitle(e.target.value)}
                                    className="bg-slate-800 border-slate-700 text-lg"
                                    autoFocus
                                />
                            </div>
                            <div>
                                <Input
                                    placeholder="Description (optional)"
                                    value={newDescription}
                                    onChange={(e) => setNewDescription(e.target.value)}
                                    className="bg-slate-800 border-slate-700"
                                />
                            </div>
                            <div className="flex gap-4 items-end">
                                <div className="flex-1">
                                    <label className="block text-xs text-slate-400 mb-1.5">Due Date & Time</label>
                                    <input
                                        type="datetime-local"
                                        value={newDueAt}
                                        onChange={(e) => setNewDueAt(e.target.value)}
                                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-slate-400 mb-1.5">Priority</label>
                                    <select
                                        value={newPriority}
                                        onChange={(e) => setNewPriority(e.target.value)}
                                        className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    >
                                        <option value="low">🟢 Low</option>
                                        <option value="medium">🟡 Medium</option>
                                        <option value="high">🔴 High</option>
                                    </select>
                                </div>
                                <div className="flex gap-2">
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="border-slate-700"
                                        onClick={() => setShowForm(false)}
                                    >
                                        Cancel
                                    </Button>
                                    <Button
                                        type="submit"
                                        disabled={submitting || !newTitle.trim()}
                                        className="bg-blue-600 hover:bg-blue-700"
                                    >
                                        {submitting ? "Adding..." : "Add Task"}
                                    </Button>
                                </div>
                            </div>
                        </form>
                    </CardContent>
                </Card>
            )}

            {/* Filter Tabs */}
            <div className="border-b border-slate-800">
                <div className="flex gap-6">
                    {(["all", "active", "completed"] as FilterTab[]).map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setFilter(tab)}
                            className={`pb-3 border-b-2 font-medium text-sm capitalize transition-colors ${filter === tab
                                ? "border-blue-600 text-blue-500"
                                : "border-transparent text-slate-400 hover:text-slate-300"
                                }`}
                        >
                            <div className="flex items-center gap-2">
                                {tab === "all" && <Filter className="h-3.5 w-3.5" />}
                                {tab === "active" && <Circle className="h-3.5 w-3.5" />}
                                {tab === "completed" && <CheckCircle2 className="h-3.5 w-3.5" />}
                                {tab}
                                <span className="text-xs bg-slate-800 px-2 py-0.5 rounded-full">
                                    {tab === "all"
                                        ? todos.length
                                        : tab === "active"
                                            ? activeTodos.length
                                            : completedTodos.length}
                                </span>
                            </div>
                        </button>
                    ))}
                </div>
            </div>

            {/* Todo List */}
            {loading ? (
                <div className="text-center py-12 text-slate-400">
                    <div className="animate-pulse">Loading tasks...</div>
                </div>
            ) : filteredTodos.length === 0 ? (
                <Card className="bg-slate-900/50 border-slate-800">
                    <CardContent className="py-16 text-center">
                        <CheckCircle2 className="h-12 w-12 text-slate-600 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-slate-300 mb-2">
                            {filter === "completed" ? "No completed tasks yet" : "No tasks yet"}
                        </h3>
                        <p className="text-slate-500 mb-4">
                            {filter === "completed"
                                ? "Complete some tasks and they'll appear here"
                                : "Add a task above or ask the AI to create one in chat"}
                        </p>
                        {filter !== "completed" && (
                            <Button
                                onClick={() => setShowForm(true)}
                                className="bg-blue-600 hover:bg-blue-700"
                            >
                                <Plus className="h-4 w-4 mr-2" />
                                Add your first task
                            </Button>
                        )}
                    </CardContent>
                </Card>
            ) : (
                <div className="space-y-2">
                    {filteredTodos.map((todo) => {
                        const dueInfo = formatDue(todo.due_at)
                        const prio = priorityConfig[todo.priority] || priorityConfig.medium
                        const src = sourceLabel[todo.source] || ""

                        return (
                            <div
                                key={todo.id}
                                className={`group flex items-center gap-4 px-5 py-4 rounded-xl border transition-all ${todo.is_completed
                                    ? "bg-slate-900/30 border-slate-800/50"
                                    : "bg-slate-900/50 border-slate-800 hover:border-slate-700"
                                    }`}
                            >
                                {/* Check button */}
                                <button
                                    onClick={() => handleToggle(todo)}
                                    className="flex-shrink-0 transition-colors"
                                >
                                    {todo.is_completed ? (
                                        <CheckCircle2 className="h-5 w-5 text-green-500" />
                                    ) : (
                                        <Circle className="h-5 w-5 text-slate-500 hover:text-blue-400" />
                                    )}
                                </button>

                                {/* Content */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                        <span
                                            className={`text-sm font-medium ${todo.is_completed
                                                ? "text-slate-500 line-through"
                                                : "text-white"
                                                }`}
                                        >
                                            {todo.title}
                                        </span>
                                        {!todo.is_completed && (
                                            <span className={`h-2 w-2 rounded-full ${prio.dot}`} title={prio.label} />
                                        )}
                                        {src && (
                                            <span className="text-xs text-slate-500">{src}</span>
                                        )}
                                        {todo.gcal_event_id && (
                                            <span title="Synced to Google Calendar">
                                                <Calendar className="h-3 w-3 text-blue-400" />
                                            </span>
                                        )}
                                    </div>
                                    {todo.description && (
                                        <p className="text-xs text-slate-500 mt-0.5 truncate">
                                            {todo.description}
                                        </p>
                                    )}
                                    {dueInfo && (
                                        <div className={`flex items-center gap-1 mt-1 text-xs ${dueInfo.color}`}>
                                            <Clock className="h-3 w-3" />
                                            {dueInfo.text}
                                        </div>
                                    )}
                                </div>

                                {/* Delete */}
                                <button
                                    onClick={() => handleDelete(todo.id)}
                                    className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity text-slate-500 hover:text-red-400"
                                >
                                    <Trash2 className="h-4 w-4" />
                                </button>
                            </div>
                        )
                    })}
                </div>
            )}

            {/* Toast */}
            {toast && (
                <div
                    className={`fixed bottom-6 right-6 px-6 py-4 rounded-lg shadow-lg border animate-in slide-in-from-bottom-5 ${toast.type === "success"
                        ? "bg-green-900/90 border-green-700 text-green-100"
                        : "bg-red-900/90 border-red-700 text-red-100"
                        }`}
                >
                    <p className="font-medium">{toast.message}</p>
                </div>
            )}
        </div>
    )
}
