# Math Class Agent
An agent that funs the MatLab compiler in the background in addition to custom MatLab files. Starting with Linear Algebra. 

## Math Problems 
* Gaussian Elimination

## Math Questions
* What are linear combinations and why are vectors and matrices important?
* What does it mean to say vectors *v* and *w* are linearly independent?
* How do we know when 3 vectors fill a plane within a 3-dimensional space?
* What is the Schwarz Inequality and the Triangle Inequality and how are they related?
* What is the relationship between row picture and the dot product? Explain the cosine formula and how it illustrates whether unit vectors are perpendicular or parallel?
* Where dos the row picture of A*x* come from? Where does the column picture come from?
* In matrix multiplication, why is matrix *AB* usually different from *BA*?
  
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
# Major Advice Agent
**Goal:** 
**Endpoint:** `POST /a2a`

## Quick Start 
Within your `.venv` run: 
```
python3 langchain_majoradvice.py
```

## Curl Commands

```
curl -sS -X POST 'http://127.0.0.1:6000/a2a' \
  -H 'Content-Type: application/json' \
  --data-binary '{"role":"user","parts":[{"type":"text","text":"@agent123 I need help selecting a college major"}]}'
```
