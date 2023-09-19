## Install

Create and activate virtual env

```bash
python -m venv .venv
source .venv/bin/activate
```

Install

```bash
pip install -e .
```

Set environment for OPENAI API Key, optionally for Lanchain API for langsmith

```
OPENAI_API_KEY=
LANGCHAIN_API_KEY=
```

Run
```
python src/query.py
```
