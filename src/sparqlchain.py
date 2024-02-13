"""
Question answering over an RDF or OWL graph using SPARQL.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
#import pydantic as pydantic_v1
from pydantic import Field
from langchain.prompts.prompt import PromptTemplate
from langchain.callbacks.manager import CallbackManagerForChainRun
from langchain.chains.base import Chain
from langchain.chains.graph_qa.prompts import (
    SPARQL_GENERATION_SELECT_PROMPT,
    SPARQL_GENERATION_UPDATE_PROMPT,
    SPARQL_INTENT_PROMPT,
    SPARQL_QA_PROMPT,
)
from langchain.chains.llm import LLMChain
#from langchain.graphs.rdf_graph import RdfGraph
from rdfgraph import RdfGraph
from langchain.prompts.base import BasePromptTemplate
from langchain.schema.language_model import BaseLanguageModel
import validators


SPARQL_ENDPOINT_TEMPLATE = """Task: Identify the SPARQL endpoint and return the appropriate SPARQL endpoint URL.
You are an assistant that can extract a SPARQL endpoint URL from the prompt.

For example, the input text could be:
Using Wikidata (https://wikidata.org/sparql) to answer the question, what movies has Johnny Depp appeared in?

The answer would be: https://wikidata.org/sparql

Note: Be as concise as possible.
Do not include any explanations or apologies in your responses.
Do not respond to any questions that ask for anything else than for you to extract the SPARQL Endpoint URL.
Do not include any unnecessary whitespaces or any text except the URL.
If there is not URL in the prompt. Then respond with "No URL found".

The prompt is:
{prompt}
Helpful Answer:"""
SPARQL_ENDPOINT_PROMPT = PromptTemplate(
    input_variables=["prompt"], template=SPARQL_ENDPOINT_TEMPLATE
)


class MyGraphSparqlQAChain(Chain):
    """
    Chain for question-answering against an RDF or OWL graph by generating
    SPARQL statements.
    """

    graph: RdfGraph = Field(exclude=True)
    sparql_generation_select_chain: LLMChain
    sparql_generation_update_chain: LLMChain
    sparql_intent_chain: LLMChain
    sparql_endpoint_chain: LLMChain
    qa_chain: LLMChain
    input_key: str = "query"  #: :meta private:
    output_key: str = "result"  #: :meta private:

    @property
    def input_keys(self) -> List[str]:
        return [self.input_key]

    @property
    def output_keys(self) -> List[str]:
        _output_keys = [self.output_key]
        return _output_keys

    @classmethod
    def from_llm(
        cls,
        llm: BaseLanguageModel,
        *,
        qa_prompt: BasePromptTemplate = SPARQL_QA_PROMPT,
        sparql_select_prompt: BasePromptTemplate = SPARQL_GENERATION_SELECT_PROMPT,
        sparql_update_prompt: BasePromptTemplate = SPARQL_GENERATION_UPDATE_PROMPT,
        sparql_intent_prompt: BasePromptTemplate = SPARQL_INTENT_PROMPT,
        sparql_endpoint_prompt: BasePromptTemplate = SPARQL_ENDPOINT_PROMPT,
        
        **kwargs: Any,
    ) -> MyGraphSparqlQAChain:
        """Initialize from LLM."""
        qa_chain = LLMChain(llm=llm, prompt=qa_prompt)
        sparql_generation_select_chain = LLMChain(llm=llm, prompt=sparql_select_prompt)
        sparql_generation_update_chain = LLMChain(llm=llm, prompt=sparql_update_prompt)
        sparql_intent_chain = LLMChain(llm=llm, prompt=sparql_intent_prompt)
        sparql_endpoint_chain = LLMChain(llm=llm, prompt=sparql_endpoint_prompt)

        return cls(
            qa_chain=qa_chain,
            sparql_generation_select_chain=sparql_generation_select_chain,
            sparql_generation_update_chain=sparql_generation_update_chain,
            sparql_intent_chain=sparql_intent_chain,
            sparql_endpoint_chain=sparql_endpoint_chain,
            **kwargs,
        )

    def _call(
        self,
        inputs: Dict[str, Any],
        run_manager: Optional[CallbackManagerForChainRun] = None,
    ) -> Dict[str, str]:
        """
        Generate SPARQL query, use it to retrieve a response from the sparql endpoint and answer
        the question.
        """
        _run_manager = run_manager or CallbackManagerForChainRun.get_noop_manager()
        callbacks = _run_manager.get_child()
        query = inputs['query']
        context = inputs['context']
        prompt = query + context
        #prompt = inputs[self.input_key]

        _run_manager.on_text("Query:", end="\n", verbose=self.verbose)
        _run_manager.on_text(query, color="green", end="\n", verbose=self.verbose)

        _endpoint = self.sparql_endpoint_chain.run({"prompt": query}, callbacks=callbacks)
        endpoint = _endpoint.strip()
        if endpoint.find("http") == -1:
            raise ValueError(
                "I am sorry, but this prompt does not specify any http based endpoint"
            )
        if not validators.url(endpoint):
            raise ValueError(
                "I am sorry, but the URL provided does not appear to be valid"
            )
        # check if endpoint is valid
        self.graph.query_endpoint = endpoint
        _run_manager.on_text("SPARQL Endpoint:", end="\n", verbose=self.verbose)
        _run_manager.on_text(endpoint, color="green", end="\n", verbose=self.verbose)

        _intent = self.sparql_intent_chain.run({"prompt": prompt}, callbacks=callbacks)
        intent = _intent.strip()

        if "SELECT" not in intent and "UPDATE" not in intent:
            raise ValueError(
                "I am sorry, but this prompt seems to fit none of the currently "
                "supported SPARQL query types, i.e., SELECT and UPDATE."
            )
        elif intent.find("SELECT") != -1:
            sparql_generation_chain = self.sparql_generation_select_chain
            intent = "SELECT"
        else:
            sparql_generation_chain = self.sparql_generation_update_chain
            intent = "UPDATE"

        _run_manager.on_text("Identified intent:", end="\n", verbose=self.verbose)
        _run_manager.on_text(intent, color="green", end="\n", verbose=self.verbose)

        generated_sparql = sparql_generation_chain.run(
            {"prompt": prompt, "schema": self.graph.get_schema}, callbacks=callbacks
        )
        if self.graph.checkSPARQLQuery(generated_sparql) is False:
            raise ValueError(
                "I am sorry, but the generated SPARQL query is invalid."
            )
            ### we will try again

        _run_manager.on_text("Generated SPARQL:", end="\n", verbose=self.verbose)
        _run_manager.on_text(
            generated_sparql, color="green", end="\n", verbose=self.verbose
        )
        ### check validity of generated SPARQL

        if intent == "SELECT":
            context = self.graph.query(generated_sparql)

            _run_manager.on_text("Full Context:", end="\n", verbose=self.verbose)
            _run_manager.on_text(
                str(context), color="green", end="\n", verbose=self.verbose
            )
            result = self.qa_chain(
                {"prompt": prompt, "context": context},
                callbacks=callbacks,
            )
            res = result[self.qa_chain.output_key]
        elif intent == "UPDATE":
            self.graph.update(generated_sparql)
            res = "Successfully inserted triples into the graph."
        else:
            raise ValueError("Unsupported SPARQL query type.")
        return {self.output_key: res}

