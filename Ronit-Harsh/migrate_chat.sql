-- Run this in the Supabase SQL Editor to enable Chat History

-- 1. Create 'chats' table
CREATE TABLE IF NOT EXISTS public.chats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Create 'messages' table
CREATE TABLE IF NOT EXISTS public.messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    chat_id UUID NOT NULL REFERENCES public.chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- 'user' or 'ai'
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Enable Row Level Security (RLS)
ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- 4. Policies
-- Create policy only if it doesn't exist (using DO block to avoid errors if re-run)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'chats' AND policyname = 'Users can only access their own chats'
    ) THEN
        CREATE POLICY "Users can only access their own chats" ON public.chats FOR ALL USING (auth.uid() = user_id);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'messages' AND policyname = 'Users can only access messages from their own chats'
    ) THEN
        CREATE POLICY "Users can only access messages from their own chats" ON public.messages FOR ALL USING (
            EXISTS (
                SELECT 1 FROM public.chats
                WHERE public.chats.id = public.messages.chat_id
                AND public.chats.user_id = auth.uid()
            )
        );
    END IF;
END
$$;

-- 5. Indexes
CREATE INDEX IF NOT EXISTS idx_chats_user ON public.chats(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_chat ON public.messages(chat_id);
