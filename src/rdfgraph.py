from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    List,
    Optional,
)

if TYPE_CHECKING:
    import rdflib


prefixes = {
    "owl": """PREFIX owl: <http://www.w3.org/2002/07/owl#>\n""",
    "rdf": """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n""",
    "rdfs": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n""",
    "xsd": """PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n""",
    "dct": """PREFIX dct: <http://purl.org/dc/terms/>\n"""
}

from_restriction = """FROM <http://bio2rdf.org/drugbank_resource:bio2rdf.dataset.drugbank.R3>\n"""

cls_query_owl = prefixes["rdfs"] + prefixes['dct'] + (
"""
SELECT ?entity ?label
{
  {{
        SELECT DISTINCT ?entity 
        FROM_RESTRICTION
        { ?s ?entity ?o .}
  }}
  ?entity dct:title ?label .
}
""".replace("FROM_RESTRICTION",from_restriction)
)

op_query_owl = (prefixes["rdfs"]+ prefixes["owl"] + prefixes['dct'] + (
"""
SELECT ?entity ?label
{
  {{
        SELECT DISTINCT ?entity 
        FROM_RESTRICTION
        {?entity a owl:ObjectProperty .}
  }}
  ?entity dct:title ?label .
}
""".replace("FROM_RESTRICTION",from_restriction)
))

dp_query_owl = (prefixes["rdfs"] + prefixes["owl"] + prefixes['dct'] + (
"""
SELECT ?entity ?label
{
  {{
        SELECT DISTINCT ?entity 
        FROM_RESTRICTION
        {?entity a owl:DatatypeProperty .}
  }}
  ?entity dct:title ?label .
}
""".replace("FROM_RESTRICTION",from_restriction)
))


class RdfGraph:
    """
    RDFlib wrapper for graph operations.
    Modes:
    * local: Local file - can be queried and changed
    * online: Online file - can only be queried, changes can be stored locally
    * store: Triple store - can be queried and changed if update_endpoint available
    Together with a source file, the serialization should be specified.
    """

    def __init__(
        self,
        source_file: Optional[str] = None,
        serialization: Optional[str] = "ttl",
        query_endpoint: Optional[str] = None,
        update_endpoint: Optional[str] = None,
        standard: Optional[str] = "rdf",
        local_copy: Optional[str] = None,
    ) -> None:
        """
        Set up the RDFlib graph

        :param source_file: either a path for a local file or a URL
        :param serialization: serialization of the input
        :param query_endpoint: SPARQL endpoint for queries, read access
        :param update_endpoint: SPARQL endpoint for UPDATE queries, write access
        :param standard: RDF, RDFS, or OWL
        :param local_copy: new local copy for storing changes
        """
        self.source_file = source_file
        self.serialization = serialization
        self.query_endpoint = query_endpoint
        self.update_endpoint = update_endpoint
        self.standard = standard
        self.local_copy = local_copy

        try:
            import rdflib
            from rdflib.graph import DATASET_DEFAULT_GRAPH_ID as default
            from rdflib.plugins.stores import sparqlstore
        except ImportError:
            raise ValueError(
                "Could not import rdflib python package. "
                "Please install it with `pip install rdflib`."
            )
        if self.standard not in (supported_standards := ("rdf", "rdfs", "owl")):
            raise ValueError(
                f"Invalid standard. Supported standards are: {supported_standards}."
            )

        if (
            not source_file
            and not query_endpoint
            or source_file
            and (query_endpoint or update_endpoint)
        ):
            raise ValueError(
                "Could not unambiguously initialize the graph wrapper. "
                "Specify either a file (local or online) via the source_file "
                "or a triple store via the endpoints."
            )

        if source_file:
            if source_file.startswith("http"):
                self.mode = "online"
            else:
                self.mode = "local"
                if self.local_copy is None:
                    self.local_copy = self.source_file
            self.graph = rdflib.Graph()
            self.graph.parse(source_file, format=self.serialization)

        if query_endpoint:
            self.mode = "store"
            if not update_endpoint:
                self._store = sparqlstore.SPARQLStore()
                self._store.open(query_endpoint)
            else:
                self._store = sparqlstore.SPARQLUpdateStore()
                self._store.open((query_endpoint, update_endpoint))
            self.graph = rdflib.Graph(self._store) #, identifier=default)

        # Verify that the graph was loaded
        #if not len(self.graph):
        #    raise AssertionError("The graph is empty.")

        # Set schema
        self.schema = ""
        #self.load_schema()

    @property
    def get_schema(self) -> str:
        """
        Returns the schema of the graph database.
        """
        return self.schema

    def query(
        self,
        query: str,
    ) -> List[rdflib.query.ResultRow]:
        """
        Query the graph.
        """
        from rdflib.exceptions import ParserError
        from rdflib.query import ResultRow

        try:
            res = self.graph.query(query)
        except ParserError as e:
            raise ValueError("Generated SPARQL statement is invalid\n" f"{e}")
        return [r for r in res if isinstance(r, ResultRow)]

    def update(
        self,
        query: str,
    ) -> None:
        """
        Update the graph.
        """
        from rdflib.exceptions import ParserError

        try:
            self.graph.update(query)
        except ParserError as e:
            raise ValueError("Generated SPARQL statement is invalid\n" f"{e}")
        if self.local_copy:
            self.graph.serialize(
                destination=self.local_copy, format=self.local_copy.split(".")[-1]
            )
        else:
            raise ValueError("No target file specified for saving the updated file.")

    @staticmethod
    def _get_local_name(iri: str) -> str:
        if "#" in iri:
            local_name = iri.split("#")[-1]
        elif "/" in iri:
            local_name = iri.split("/")[-1]
            if ":" in local_name:
                local_name = local_name.split(":")[-1]
        else:
            raise ValueError(f"Unexpected IRI '{iri}', contains neither '#' nor '/'.")
        return local_name

    def _res_to_str(self, res: rdflib.query.ResultRow, var: str) -> str:
        return (
            "<"
            + str(res[var])
            + "> ("
            # + self._get_local_name(res[var])
            # + ", "
            + str(res["label"])
            + ")"
        )

    def load_schema(self) -> None:
        """
        Load the graph schema information.
        """

        if self.standard == "owl":
            clss = self.query(cls_query_owl)
            ops = self.query(op_query_owl)
            dps = self.query(dp_query_owl)
            self.schema = (
                f"In the following, each IRI is followed its label in parentheses.\n "
                f"The OWL graph supports the following node types:\n"
                f'{", ".join([self._res_to_str(r, "entity") for r in clss])}\n'
                f"The OWL graph supports the following object properties, "
                f"i.e., relationships between objects:\n"
                f'{", ".join([self._res_to_str(r, "entity") for r in ops])}\n'
                f"The OWL graph supports the following data properties, "
                f"i.e., relationships between objects and literals:\n"
                f'{", ".join([self._res_to_str(r, "entity") for r in dps])}\n'
            )
        else:
            raise ValueError(f"Mode '{self.standard}' is currently not supported.")
