# Linear Algebra Agent
**Goal:** Explain core Linear Algebra ideas and walk through simple problems.  
**Endpoint:** `POST /a2a`

## Quick Start 
Within your `.venv` run: 
```
python3 langchain_linearalgebra.py
```

## Curl Commands

General Langchain Command
```
curl -sS -X POST 'http://127.0.0.1:6000/a2a' \
  -H 'Content-Type: application/json' \
  --data-binary '{"role":"user","parts":[{"type":"text","text":"Please explain what linear algebra is and show Gaussian elimination on [[2,1],[5,3]]."}]}'
```

LangChain Math Command
```
curl -sS -X POST http://localhost:6000/a2a \             
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": { "type": "text",
      "text": "@AGENT A=[[2,1,-1],[-3,-1,2],[-2,1,2]]\nb=[8,-11,-3]\nsteps=full"
    }
  }'
```

MatLab Defaults Command
```
curl -sS -X POST http://localhost:6000/a2a \      
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": { "type": "text",
      "text": "@AGENT A=[[2,1,-1],[-3,-1,2],[-2,1,2]]\n b=[8,-11,-3]"
    }
  }'
```

OpenAI Command
```
curl -sS -X POST http://127.0.0.1:6000/a2a \                                     ─╯
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": { "type": "text",
      "text": "@AGENT Solve with Gaussian elimination.\nA=[[2,1,-1],[-3,-1,2],[-2,1,2]]\nb=[8,-11,-3]\nsteps=full"
    }
  }'
```
