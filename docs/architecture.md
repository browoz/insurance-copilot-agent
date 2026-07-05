# Architecture

## Flow

```text
User question
  -> SQL search over plan facts
  -> TF-IDF keyword retrieval over glossary docs
  -> SVD vector retrieval over glossary docs
  -> prompt builder
  -> Mistral API
  -> answer + citations + plan table
```

## Why This Design

SQL handles facts and numbers:
- state
- county
- plan type
- metal level
- premium
- deductible

RAG handles explanations:
- premium
- deductible
- out-of-pocket maximum
- metal level
- plan selection tradeoffs

This avoids the common mistake of using vector search for numeric filtering.

