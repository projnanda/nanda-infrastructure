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
  
## Configuration
Retrieve an [Anthropic Key](https://console.anthropic.com). Set your `ANTHROPIC_API_KEY` environment variable
```
export ANTHROPIC_API_KEY="YOUR KEY HERE"
```

## Installation
Clone the repository
```
git clone https://github.com/projnanda/nanda-infrastructure
```

Install the NANDA SDK
```
pip install nanda-sdk
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
🚀 Starting Agent default bridge on port 8000
Agent terminal port: 6010
Message improvement feature is ENABLED
Logging conversations to /Users/debbieyuen/Documents/Personal Projects/radiusfellow/adapter-edge-sdk/nanda_adapter/examples/conversation_logs
🔧 Using custom improvement logic: pirate_improvement
Starting A2A server on http://0.0.0.0:8000/a2a
```

## Resources
* Agent Development Kit (ADK) Samples
* [NANDA-SDK](https://github.com/projnanda/nanda-sdk?tab=readme-ov-file)
* [DuckDNS](https://www.duckdns.org/domains)
* [AWS EC2](https://us-east-2.signin.aws.amazon.com)
* [Chat-NANDA-registry](https://chat.nanda-registry.com/index.html)
* [Build with Claude](https://docs.anthropic.com/en/home)
  
## License
MIT License

Copyright (c) 2024 Internet of Agents

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


