# AusLaw AI

An Australian Legal Assistant MVP that provides legal information, lawyer matching, step-by-step checklists, and document analysis for legal procedures across Australian states/territories.

## Features

- **Legal Research**: RAG-powered search of Australian legislation with hybrid retrieval (vector + full-text search)
- **Lawyer Matching**: Find lawyers by specialty and location
- **Procedure Checklists**: Generate step-by-step guides for legal processes
- **Document Analysis**: Upload and analyze legal documents (PDF, DOCX, images)
- **State-Aware**: All information is tailored to the user's Australian state/territory

## Tech Stack

- **Frontend**: Next.js 14, CopilotKit, shadcn/ui, Tailwind CSS
- **Backend**: FastAPI, LangGraph, langchain-openai (GPT-4o)
- **Database**: Supabase PostgreSQL with pgvector for RAG
- **Storage**: Supabase Storage for document uploads

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+ with conda
- Supabase account
- OpenAI API key

### Setup

1. **Clone and install**
   ```bash
   git clone <repo-url>
   cd law_agent

   # Frontend
   cd frontend && npm install

   # Backend
   cd ../backend
   conda create -n law_agent python=3.11
   conda activate law_agent
   pip install -r requirements.txt
   ```

2. **Environment variables**

   Create `backend/.env`:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   OPENAI_API_KEY=your_openai_key
   COHERE_API_KEY=your_cohere_key  # Optional: for reranking
   ```

   Create `frontend/.env.local`:
   ```
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
   ```

3. **Database setup**

   Run the following SQL files in Supabase SQL Editor:
   - `database/setup.sql` - Initial schema and mock data
   - `database/migration_v2.sql` - Action templates table
   - `database/migration_rag.sql` - pgvector schema for RAG

4. **Ingest legal corpus** (optional, for RAG)
   ```bash
   cd backend
   conda activate law_agent
   python scripts/ingest_corpus.py --limit 100  # Test with 100 docs
   ```

5. **Run**
   ```bash
   # Terminal 1 - Backend
   cd backend && conda activate law_agent && python main.py

   # Terminal 2 - Frontend
   cd frontend && npm run dev
   ```

6. Open http://localhost:3000

Docker backend build note:
```bash
# Build from repo root so local framework package is included
docker build -f backend/Dockerfile .
```

## Transport-Neutral Framework Runner

In addition to the CopilotKit path, the backend now exposes a stack-agnostic
framework endpoint and a local reference client.

Framework extraction status:
- Standalone package source now lives at `packages/legal-agent-framework/src/legal_agent_framework`.
- Backend now imports `legal_agent_framework` directly.
- Backend dependency includes local editable package path:
  - `-e ../packages/legal-agent-framework` (in `backend/requirements.txt`)
- Optional explicit install for external consumers:
  - `pip install -e packages/legal-agent-framework`

- API endpoint: `POST /framework/run`
- Payload contract:
  - `messages`: transport-neutral chat history (`role`, `content`)
  - `request_context`: transport-neutral context (`user_state`, `ui_mode`, `legal_topic`, ...)
  - `trace_id` (optional): continue an existing trace stream across turns
  - `trace_events` (optional): prior events to replay/continue
- Response includes:
  - `trace_id`: active trace identifier for this run
  - `trace_events`: ordered structured events emitted by wrapped stages
- Auth: same bearer token auth as other protected backend routes
- Optional provider selection (no code changes required):
  - `LAW_FRAMEWORK_STAGE_PROVIDER=<registered_stage_provider_name>`
  - `LAW_FRAMEWORK_TOOL_PROVIDER=<registered_tool_provider_name>`
  - Built-in provider names:
    - `auslaw_default` (current production app behavior)
    - `demo_minimal` (deterministic demo provider)

Example request:

```bash
curl -X POST http://localhost:8000/framework/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <supabase_access_token>" \
  -d '{
    "messages": [{"role":"user","content":"I got a parking fine, what can I do?"}],
    "request_context": {"user_state":"NSW","ui_mode":"analysis","legal_topic":"parking_ticket"},
    "trace_id": "session-trace-001"
  }'
```

Local non-CopilotKit reference client:

```bash
cd backend
python scripts/run_framework_local.py \
  --message "I got a parking fine, what can I do?" \
  --state NSW \
  --mode analysis \
  --topic parking_ticket
```

Run with demo provider (no LLM/tool backend dependencies):

```bash
export LAW_FRAMEWORK_STAGE_PROVIDER=demo_minimal
export LAW_FRAMEWORK_TOOL_PROVIDER=demo_minimal
python scripts/run_framework_local.py --message "What are my options?" --state NSW
```

## Architecture

```
Frontend (Next.js)  →  /api/copilotkit  →  FastAPI Backend  →  Supabase
     ↓                      ↓                    ↓
CopilotChat         HttpAgent proxy      Custom LangGraph
+ StateSelector     (AG-UI protocol)     (CopilotKitState)
+ FileUpload                                   ↓
+ useCopilotReadable              Tools: lookup_law, find_lawyer,
                                  generate_checklist, analyze_document
```

## RAG System

The `lookup_law` tool uses a hybrid retrieval pipeline:
1. **Hybrid Search**: Vector similarity (pgvector) + PostgreSQL full-text search
2. **RRF Fusion**: Reciprocal Rank Fusion merges results from both methods
3. **Reranking**: Optional Cohere rerank for final precision

**Data Source**: [Open Australian Legal Corpus](https://huggingface.co/datasets/isaacus/open-australian-legal-corpus) (Primary Legislation)

**Supported Jurisdictions**: NSW, QLD, Federal (others fall back to Federal law)

## License

MIT
