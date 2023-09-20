This project aims to create a general purpose [LangChain](langchain.com) component to perform queries over large SPARQL endpoints.
It derives from the existing [GraphSPARQLQAChain](https://python.langchain.com/docs/use_cases/more/graph/graph_sparql_qa), but
aims to address some shortcomings including dealing with very large schemas, improved schema guidance, and better quality answers 
for existing SPARQL endpoints such as [Bio2RDF](https://bio2rdf.org) and [Wikidata](https://wikidata.org).

Current status:
* This project is in pre-alpha and is demonstrative of the approach. 

Future work:
* Refactor the context generation to remove hardcoding of bio2rdf schema and instructions.
* Be able to specify a target SPARQL endpoint to query against.
* Generate, store, and load an RDF schema for a SPARQL endpoint.
* Identify a relevant fragment of the schema to guide the construction.
* Use other LLMs such as LLAMA2 instead of OpenAI GPT
* Iterate until a valid SPARQL query can be generated
* Implement a conversational AI to i) improve query answering and ii) support human feedback reinforcement learning.

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
