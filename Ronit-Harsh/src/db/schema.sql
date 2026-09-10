-- ⚠️ DESTRUCTIVE: DROP TABLES TO START FRESH
DROP TABLE IF EXISTS public.embeddings CASCADE;
DROP TABLE IF EXISTS public.inbox_items CASCADE;
DROP TABLE IF EXISTS public.courses CASCADE;
DROP TABLE IF EXISTS public.user_integrations CASCADE;

-- 1. Enable Vector Extension (for Embeddings)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create 'user_integrations' table
CREATE TABLE public.user_integrations (
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL, -- 'google_classroom'
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    sync_status TEXT DEFAULT 'idle', -- 'in_progress', 'success', 'error'
    sync_progress INTEGER DEFAULT 0,
    last_synced_at TIMESTAMP WITH TIME ZONE,
    
    PRIMARY KEY (user_id, provider)
);

-- 3. Create 'courses' table
CREATE TABLE public.courses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    classroom_id TEXT NOT NULL, -- "MA2150"
    name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    
    UNIQUE(user_id, classroom_id) -- A user can't have the same course twice
);

-- 4. Create 'inbox_items' table
CREATE TABLE public.inbox_items (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY, -- UUIDv5 from Google ID
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    course_id UUID REFERENCES public.courses(id) ON DELETE CASCADE,
    
    -- Core Fields
    external_id TEXT NOT NULL, -- Google Classroom Item ID
    source TEXT DEFAULT 'CLASSROOM',
    type TEXT, -- ASSIGNMENT, ANNOUNCEMENT, MATERIAL
    title TEXT,
    description TEXT,
    due_date TIMESTAMP WITH TIME ZONE,
    
    -- Attachments (Drive files, YouTube, Links)
    files_data JSONB DEFAULT '[]'::jsonb, 
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    
    UNIQUE(user_id, external_id)
);

-- 5. Create 'embeddings' table (pgvector)
CREATE TABLE public.embeddings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    item_id UUID REFERENCES public.inbox_items(id) ON DELETE CASCADE,
    
    content TEXT, -- The actual chunk of text
    embedding vector(768), -- OpenAI=1536, all-mpnet-base-v2=768
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexes
CREATE INDEX idx_courses_user ON public.courses(user_id);
CREATE INDEX idx_inbox_items_user ON public.inbox_items(user_id);
CREATE INDEX idx_embeddings_user ON public.embeddings(user_id);
-- HNSW Index for fast vector search (Optional but recommended for performance)
-- CREATE INDEX ON public.embeddings USING hnsw (embedding vector_cosine_ops);

-- 6. RPC Function for Vector Search
CREATE OR REPLACE FUNCTION match_embeddings (
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  _user_id uuid,
  _course_id uuid DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  content text,
  similarity float,
  item_id uuid,
  title text,
  type text,
  files_data jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    e.id,
    e.content,
    1 - (e.embedding <=> query_embedding) as similarity,
    i.id as item_id,
    i.title,
    i.type,
    i.files_data
  FROM embeddings e
  JOIN inbox_items i ON e.item_id = i.id
  WHERE e.user_id = _user_id
  AND (1 - (e.embedding <=> query_embedding) > match_threshold)
  AND (_course_id IS NULL OR i.course_id = _course_id)
  ORDER BY e.embedding <=> query_embedding
  LIMIT match_count;
END;

-- 7. Create 'chats' table
CREATE TABLE public.chats (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 8. Create 'messages' table
CREATE TABLE public.messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    chat_id UUID NOT NULL REFERENCES public.chats(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- 'user' or 'ai'
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 9. Enable Row Level Security (RLS) & Policies
ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;

-- Chats Policy: Users can only see their own chats
CREATE POLICY "Users can only access their own chats"
ON public.chats
FOR ALL
USING (auth.uid() = user_id);

-- Messages Policy: Users can only see messages from their own chats
-- Note: We join with chats to verify ownership
CREATE POLICY "Users can only access messages from their own chats"
ON public.messages
FOR ALL
USING (
  EXISTS (
    SELECT 1 FROM public.chats
    WHERE public.chats.id = public.messages.chat_id
    AND public.chats.user_id = auth.uid()
  )
);

-- Indexes for performance
CREATE INDEX idx_chats_user ON public.chats(user_id);
CREATE INDEX idx_messages_chat ON public.messages(chat_id);

-- 10. Add scholr calendar ID to user_integrations
ALTER TABLE public.user_integrations 
ADD COLUMN IF NOT EXISTS scholr_calendar_id TEXT;

-- 11. Create 'todos' table
CREATE TABLE public.todos (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    due_at TIMESTAMP WITH TIME ZONE,
    is_completed BOOLEAN DEFAULT FALSE,
    priority TEXT DEFAULT 'medium',        -- 'low', 'medium', 'high'
    source TEXT DEFAULT 'manual',          -- 'manual', 'chat', 'classroom'
    gcal_event_id TEXT,                    -- GCal event ID on "scholr" calendar
    inbox_item_id UUID REFERENCES public.inbox_items(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE INDEX idx_todos_user ON public.todos(user_id);

-- RLS for todos
ALTER TABLE public.todos ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access their own todos"
ON public.todos FOR ALL USING (auth.uid() = user_id);
