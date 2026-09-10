import { ChatHistory } from "@/components/chat/ChatHistory"

export default function ChatLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <div className="flex h-full overflow-hidden bg-slate-950 rounded-tl-2xl border-t border-l border-slate-800 shadow-2xl mr-4 mb-4">
            <ChatHistory />
            {children}
        </div>
    )
}
