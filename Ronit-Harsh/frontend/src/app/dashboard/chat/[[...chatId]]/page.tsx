"use client"
import { useEffect } from "react"
import { ChatArea } from "@/components/chat/ChatArea"

export default function ChatPage() {
    useEffect(() => {
        document.title = "AI Chat - Student Helper"
    }, [])

    return <ChatArea />
}
