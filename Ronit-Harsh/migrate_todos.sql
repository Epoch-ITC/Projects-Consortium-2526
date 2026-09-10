-- Migration: Add Google Calendar + Todo support
-- Run this on your Supabase SQL Editor

-- 1. Add scholr calendar ID to user_integrations
ALTER TABLE public.user_integrations 
ADD COLUMN IF NOT EXISTS scholr_calendar_id TEXT;

-- 2. Create todos table
CREATE TABLE IF NOT EXISTS public.todos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    due_at TIMESTAMP WITH TIME ZONE,
    is_completed BOOLEAN DEFAULT FALSE,
    priority TEXT DEFAULT 'medium',
    source TEXT DEFAULT 'manual',
    gcal_event_id TEXT,
    inbox_item_id UUID REFERENCES public.inbox_items(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Indexes
CREATE INDEX IF NOT EXISTS idx_todos_user ON public.todos(user_id);

-- 4. RLS
ALTER TABLE public.todos ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'todos' AND policyname = 'Users can only access their own todos'
    ) THEN
        CREATE POLICY "Users can only access their own todos"
        ON public.todos FOR ALL USING (auth.uid() = user_id);
    END IF;
END
$$;
