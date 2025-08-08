# LLM Configuration Guide

The Release Page Summarizer supports LLM providers that you can switch between using environment variables:

- **Local LLM** (Ollama) - Default, runs locally, private
- **Google Gemini** - Cloud-based, powerful, requires API key

## Quick Setup

### Option 1: Local LLM (Default)
```bash
# 1. Install Ollama
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.ai/install.sh | sh

# 2. Start Ollama server
ollama serve

# 3. Pull your model (in another terminal)
ollama pull mistral

```

### Option 2: Google Gemini
```bash
# 1. Get API key from https://makersuite.google.com/app/apikey

# 2. Set environment variables
export LLM_PROVIDER=gemini
export GOOGLE_API_KEY=your-api-key-here

# or update the .env file with the same variables
```

## Switching Between Providers

### Use Local LLM (Ollama)

```bash
export LLM_PROVIDER=local
# OR unset LLM_PROVIDER (local is default)
```

### Use Google Gemini
```bash
export LLM_PROVIDER=gemini
export GOOGLE_API_KEY=your-api-key-here
```

## Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `LLM_PROVIDER` | `local`, `gemini` | `local` | Which LLM to use |
| `LLM_API_URL` | URL | `http://localhost:11434/api/generate` | Ollama API endpoint |
| `LLM_MODEL` | Model name | `mistral` | Ollama model name |
| `GOOGLE_API_KEY` | API key | (empty) | Required for Gemini |
| `GEMINI_MODEL` | Model name | `gemini-1.5-flash` | Gemini model name |
| `MAX_INPUT_TOKENS` | Number | `50000` | Max tokens per request (triggers chunking) |
| `CHUNK_SIZE` | Number | `40000` | Target size for each chunk |
| `CHUNK_OVERLAP` | Number | `1000` | Overlap between chunks for context |

### Chunking
```
Small payload (< 50k tokens)  → Process normally
Large payload (> 50k tokens)  → Split into ~40k token chunks
                              → Process with 2-second delays (Gemini)
                              → Combine into final summary
```

All existing chains automatically use the configured provider with chunking:
- `summary_chain` - Now handles large release notes automatically
- `project_summary_chain` - Chunks large project summaries
- `feature_gate_summary_chain` - Processes feature gates efficiently