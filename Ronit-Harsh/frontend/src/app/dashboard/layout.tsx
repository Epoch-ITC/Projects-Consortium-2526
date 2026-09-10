import { Sidebar } from "@/components/layout/Sidebar"
import { SyncStatusBanner } from "@/components/dashboard/SyncStatusBanner"

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <div className="flex h-screen bg-slate-950 overflow-hidden">
            <Sidebar />
            <div className="flex-1 flex flex-col min-w-0">
                <SyncStatusBanner />
                <main className="flex-1 overflow-y-auto bg-slate-950 p-8">
                    {children}
                </main>
            </div>
        </div>
    )
}
