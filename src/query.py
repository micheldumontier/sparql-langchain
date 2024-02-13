import os 
from langchain.chat_models import ChatOpenAI
#from langchain.chains import GraphSparqlQAChain
#from langchain.graphs import RdfGraph


# from langsmith import Client
# from langchain.agents import AgentType, initialize_agent, load_tools
# from langchain.callbacks.tracers.langchain import wait_for_all_tracers

from rdfgraph import RdfGraph
from sparqlchain import MyGraphSparqlQAChain

# import asyncio
from dotenv import load_dotenv
load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_PROJECT"] = "sparql"
#client = Client()

graph = RdfGraph(
    query_endpoint="https://bio2rdf.org/sparql",
    standard="owl",
    local_copy="mygraph.ttl",
)
#graph.load_schema()
#schema = graph.get_schema


chain = MyGraphSparqlQAChain.from_llm(
    ChatOpenAI(temperature=0), graph=graph, verbose=True
)

# Query: Which drugs can be used to treat hypertension? Return the drug name and indication for the first 5 results
# Answer: Answer: The drugs that can be used to treat hypertension are Latanoprost, Mecamylamine, Guanethidine, Pargyline, and Valsartan
# Query What is the mechanism of action for Lepirudin? Return the text that describes the mechanism of action. 
# Query: What are the functions of the target Prothrombin? Only retrieve 5 results.
# Query: What is the specific function of the target Prothrombin?
# Answer: The specific function of the target Prothrombin is to convert fibrinogen to fibrin and activate factors V, VII, VIII, XIII, and protein C. Additionally, when in complex with thrombomodulin, Prothrombin activates protein C.
# Query: What are the synonyms of the target Prothrombin?
# Answer: The synonyms of the target Prothrombin are Thrombin, Activated Factor II [IIa], Coagulation factor II, EC 3.4.21.5, and Prothrombin precursor
# Query: What species is the target Prothrombin from?
# Answer: The target Prothrombin is from the species Homo sapiens.

query = """
Query: Use Bio2RDF (https://bio2rdf.org/sparql) to answer the following question: What is the mechanism of action for Lepirudin?
"""

#Context: Use Bio2RDF to answer the question. 
schema = """
Schema:
Only use the following tuples to create the SPARQL query. 
The statements are written as a tuple (t1, rel, t2), where t1 is related to t2 by relation rel.

PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX dct: <http://purl.org/dc/terms/>
PREFIX dv: <http://bio2rdf.org/drugbank_vocabulary:>
PREFIX tv: <http://bio2rdf.org/taxonomy_vocabulary:>

dv:Drug dct:title xsd:Literal .
dv:Drug dv:category dv:Category .
dv:Category dct:title xsd:Literal .
dv:Drug dv:mechanism-of-action dv:Mechanism-of-action .
dv:Mechanism-of-action dct:description xsd:Literal .
dv:Drug dv:indication dv:Indication .
dv:Indication dct:description xsd:Literal .
dv:Drug dv:target dv:Target .
dv:Target dct:title xsd:Literal.
dv:Target dv:synonym xsd:Literal .
dv:Target dv:specific-function xsd:Literal .
dv:Target dv:go-function xsd:Literal .
dv:Target dv:go-component xsd:Literal .
dv:Target dv:cellular-location xsd:Literal .
dv:Target dv:x-taxonomy tv:Resource .
tv:Resource tv:scientific-name xsd:Literal .
"""

instructions = """

Instructions:
Use the schema to guide the development of the SPARQL query. 
Use RDF variables such as ?drug ?target ?indication instead of prefixed names in SPARQL queries.
Apply text search on the objects of dct:title and dct:description. 
Do not use CONTAINS directly on RDF nodes.
Return text variables in a SELECT query.
Apply the DISTINCT on variables in a SELECT query.

Only use the results from the database query to answer the question.
"""


answer = chain.run( query=query, context = schema + instructions )
print(f'Query: {query}')
print(f'Answer: {answer}')
print('done')