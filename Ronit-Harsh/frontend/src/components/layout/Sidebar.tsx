"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutGrid, MessageSquare, CheckSquare, Blocks, Folder, Settings, HelpCircle, GraduationCap } from "lucide-react"
import { useAuth } from "@/context/AuthContext"

const sidebarItems = [
    { icon: LayoutGrid, label: "Dashboard", href: "/dashboard" },
    { icon: MessageSquare, label: "Chat AI", href: "/dashboard/chat" },
    { icon: CheckSquare, label: "Tasks", href: "/dashboard/tasks" },
    { icon: GraduationCap, label: "Grades", href: "/dashboard/grades" },
    { icon: Blocks, label: "Integrations", href: "/dashboard/integrations" },
    { icon: Folder, label: "Files", href: "/dashboard/files" },
]

export function Sidebar() {
    const pathname = usePathname()
    const { user } = useAuth()

    const userName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || "Student"
    // Get initials from name
    const getInitials = (name: string) => {
        return name
            .split(' ')
            .map(part => part[0])
            .join('')
            .toUpperCase()
            .slice(0, 2)
    }
    const userInitials = getInitials(userName)

    return (
        <div className="flex h-screen w-64 flex-col bg-slate-900 text-white border-r border-slate-800">
            <div className="p-6 flex items-center gap-3">
                <div className="p-2 bg-blue-600 rounded-lg">
                    <GraduationCap className="h-6 w-6 text-white" />
                </div>
                <div>
                    <h1 className="font-bold text-lg">Student AI</h1>
                    <p className="text-xs text-slate-400">Academic Helper</p>
                </div>
            </div>

            <nav className="flex-1 px-4 space-y-2 mt-4">
                {sidebarItems.map((item) => {
                    const isActive = pathname === item.href
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${isActive
                                ? "bg-blue-600 text-white"
                                : "text-slate-400 hover:bg-slate-800 hover:text-white"
                                }`}
                        >
                            <item.icon className="h-5 w-5" />
                            {item.label}
                        </Link>
                    )
                })}
            </nav>

            <div className="p-4 border-t border-slate-800 space-y-2">
                <Link
                    href="/dashboard/settings"
                    className="flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
                >
                    <Settings className="h-5 w-5" />
                    Settings
                </Link>
                <Link
                    href="/help"
                    className="flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
                >
                    <HelpCircle className="h-5 w-5" />
                    Help
                </Link>

                <div className="mt-4 flex items-center gap-3 px-4 py-3 bg-slate-800/50 rounded-xl">
                    <div className="h-10 w-10 rounded-full bg-blue-200 flex items-center justify-center text-blue-800 font-bold">
                        {userInitials}
                    </div>
                    <div className="overflow-hidden">
                        <p className="text-sm font-medium text-white truncate">{userName}</p>
                        <p className="text-xs text-slate-400 truncate">Student Plan</p>
                    </div>
                </div>
            </div>
        </div>
    )
}
