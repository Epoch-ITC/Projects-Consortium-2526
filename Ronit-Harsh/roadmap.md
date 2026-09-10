1. The Architecture: "The Student Data Lake"We separate your data into two distinct stores:Supabase (PostgreSQL): Stores the Structure (Deadlines, Course Names, Grades, To-Do status). This is your "Source of Truth."ChromaDB (Vector Store): Stores the Knowledge (PDF text, email bodies, assignment instructions). This feeds the AI "Brain."2. Supabase Schema (The Structure)Run this SQL in your Supabase SQL Editor. This sets up the relational backbone of the application.SQL-- 1. The User Profile (Linked to Supabase Auth)
CREATE TABLE public.profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    aims_username TEXT,
    full_name TEXT,
    degree_program TEXT, -- e.g., "B.Tech CSE"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. The Course Registry (Merging AIMS + Classroom)
CREATE TABLE public.courses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id),
    course_code TEXT,       -- "CS101" (From AIMS)
    classroom_id TEXT,      -- "123456" (From Google ID)
    name TEXT,              -- "Intro to Algorithms"
    professor_name TEXT,
    schedule_json JSONB,    -- [{"day": "Mon", "time": "10:00", "room": "LH-1"}]
    current_grade FLOAT     -- Live grade from AIMS/Classroom
);

-- 3. The "Inbox" (Central Task & Notification Center)
CREATE TABLE public.inbox_items (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id),
    course_id UUID REFERENCES public.courses(id), -- Nullable (e.g., Hostel notice has no course)
    
    source TEXT,            -- 'GMAIL', 'CLASSROOM_ASSIGNMENT', 'CLASSROOM_ANNOUNCEMENT'
    external_id TEXT,       -- The Google ID (to prevent duplicates)
    
    title TEXT,
    description_summary TEXT, -- AI Generated one-liner
    
    type TEXT,              -- 'DEADLINE', 'EVENT', 'NOTICE', 'MATERIAL'
    due_date TIMESTAMP WITH TIME ZONE,     -- If applicable
    
    is_processed BOOLEAN DEFAULT FALSE, -- Has the Brain analyzed this yet?
    is_completed BOOLEAN DEFAULT FALSE, -- Did the student finish it?
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
3. ChromaDB Metadata Schema (The "Brain")To prevent the AI from "hallucinating" (mixing up Physics notes with History essays), we need strict metadata tagging in ChromaDB.The Collection Name: student_knowledgeMetadata FieldsEvery chunk of text you save must have this JSON metadata attached:FieldExamplePurposeuser_iduuid-123Security: Ensures users only query their own data.sourceclassroom_materialOrigin: Where did this come from?course_codeCS101Filter: "Limit answers to this subject only."doc_typeslide, syllabus, emailWeighting: A syllabus is more authoritative than a random email.parent_iduuid-from-supabaseLink: Connects this text back to the specific assignment in SQL.timestamp2024-12-27Freshness: "Ignore announcements older than 6 months."chunk_index5Order: Allows reconstruction of the full document if needed.Python Storage ExampleWhen you ingest a PDF from Classroom, your Python script should do this:Python# Example: Storing a chunk of a Physics Slide Deck
collection.add(
    documents=["Newton's Second Law states that F=ma..."],
    metadatas=[{
        "user_id": "user_123",
        "source": "classroom_material",
        "course_code": "PHY101",
        "doc_type": "slide_deck",
        "title": "Unit 2: Forces",
        "parent_id": "supabase_assignment_id_555",
        "timestamp": "2024-12-25"
    }],
    ids=["phy101_slide_unit2_chunk5"]
)
4. The Ingestion Pipelines (How to Fetch)A. Google Classroom (The "Heavy" Lifter)You are already fetching this. Now, you must split the incoming data:Metadata: Save the Title, Due Date, and Link into Supabase (inbox_items).Content:Detect if materials contains a Drive File.Download the PDF.Extract Text -> Chunk it -> Save to ChromaDB.Tip: If it's a YouTube link, use youtube-transcript-api to get the text.B. Gmail (Signal vs. Noise)Do not fetch every email. Use Gmail's server-side filtering to save bandwidth.The Filter Query (q parameter):Instead of fetching all, ask Google specifically:Plaintext(from:academics@college.edu OR from:warden@hostel.edu OR from:mess@college.edu) 
AND after:2024/01/01 
AND -category:promotions
Python Implementation:Pythonquery = "from:academics@college.edu is:unread"
results = service.users().messages().list(userId='me', q=query).execute()
Store: Save a summary in Supabase inbox_items (Type: 'NOTICE'). Save the full body text in ChromaDB (Type: 'EMAIL').C. AIMS (The Boilerplate)Scrape the "Course List" page.Upsert into Supabase courses table.Crucial Step: Create a logic to map the AIMS Course Code (CS101) to the Classroom Name (Intro to CS) in your DB. This ensures the system knows they are the same entity.5. Memory StrategyWe use a hybrid memory approach:Long-Term Knowledge (ChromaDB):Use Case: "What is the deadline for Math?" or "Explain the concept of Torque from the slides."Tech: Vector Search.Short-Term Conversation (Redis):Use Case: "What did I just ask?" or "Summarize that."Tech: Redis (or a simple Python deque for local dev). Store the last 10 messages with a 1-hour expiry.