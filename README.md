# Infrastructure Agents

A compilation of example agents with Langchain, Crew AI, and Google ADK. 

## Overview
The NANDA Adapter: 
* Provides a domain-specific language (DSL) for handling messages
* Enables multi-protocol translation (MCP, A2A, HTTPS, NLWeb)
* Compatible with any agent development framework (e.g., Google ADK)
* Adds discoverability, interoperability, and flexible communication
* Lets you keep full control over data and infrastructure

## Prerequisites
* Python 3.6+
* MongoDB Compass 
* Root/sudo access (for SSL certificate management)
* Port 80 available (for Let's Encrypt certificate challenge)
* NANDA SDK

## Installation
Clone the repository
```
git clone https://github.com/projnanda/nanda-infrastructure
```

Install the NANDA SDK
```
pip install nanda-sdk
```

If you are on a Mac, it may be useful to create a virtual environment
```
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install nanda-adapter langchain-anthropic anthropic langchain-core
```

Retrieve an [Anthropic Key](https://console.anthropic.com). Set your `ANTHROPIC_API_KEY` environment variable
```
export ANTHROPIC_API_KEY="YOUR KEY HERE"
```

Run the `requirements.txt` file
```
pip install -r requirements.txt
```

Run one of the files. Here we will run the example `langchain_pirate.py`
```
python3 langchain_pirate.py
```

In a new terminal tab, run the following command:
```
curl -X POST http://localhost:8000/a2a \              
  -H "Content-Type: application/json" \
  -d '{
    "role": "user",
    "content": {
      "type": "text",
      "text": "@agent123 Hello, how are you doing today?"
    }
  }'
```

If it started successfully, you should see the message below:
```
🤖 NANDA initialized with custom improvement logic: pirate_improvement
🔧 Custom improvement logic 'pirate_improvement' registered
Message improver set to: nanda_custom
✅ AgentBridge created with custom improve_message_direct: pirate_improvement
Starting Pirate Agent with LangChain...
All messages will be transformed to pirate English!
🚀 NANDA starting agent_bridge server with custom logic...
🔧 UI_CLIENT_URL:
WARNING: PUBLIC_URL environment variable not set. Agent will not be registered.

🚀 Starting Agent default bridge on port 8000
Agent terminal port: 6010
Message improvement feature is ENABLED
Logging conversations to /Users/debbieyuen/Documents/Personal Projects/radiusfellow/adapter-edge-sdk/nanda_adapter/examples/conversation_logs
🔧 Using custom improvement logic: pirate_improvement
Starting A2A server on http://0.0.0.0:8000/a2a
Google A2A compatibility: Enabled
 * Serving Flask app 'python_a2a.server.http'
 * Debug mode: off
INFO:werkzeug:WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8000
 * Running on http://10.23.111.87:8000
INFO:werkzeug:Press CTRL+C to quit
```

## Resources
* [Agent Development Kit (ADK) Samples](https://github.com/google/adk-samples)
* [NANDA-SDK](https://github.com/projnanda/nanda-sdk?tab=readme-ov-file)
* [DuckDNS](https://www.duckdns.org/domains)
* [AWS EC2](https://us-east-2.signin.aws.amazon.com)
* [Chat-NANDA-registry](https://chat.nanda-registry.com/index.html)
* [Build with Claude](https://docs.anthropic.com/en/home)
* [Anthropic Courses](https://anthropic.skilljar.com)
  
## Ideas
* MatLab
* Unity
* Unreal

## Agent Comparison
* [Wolfram 4o with ChatGPT](https://chatgpt.com/g/g-0S5FXLyFN-wolfram?model=gpt-4o)
* ChatGPT 4o
* Claude
* Grock
* [Solvely](https://solvely.ai)
* [Math AI](https://math-gpt.ai)
* [MathGPT](https://math-gpt.org)
* 
  
## License
MIT License

Copyright (c) 2024 Internet of Agents

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


