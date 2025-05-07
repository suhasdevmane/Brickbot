from SPARQLWrapper import SPARQLWrapper, JSON

# Specify the DBPedia endpoint
sparql = SPARQLWrapper("http://localhost:3030/#/dataset/ds/query")

# Query for the description of "Capsaicin", filtered by language
sparql.setQuery(
    """
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    PREFIX brk: <http://brk.basisregistraties.overheid.nl/def/brk#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT * WHERE {
        ?sub brick:hasPoint ?obj .
    } LIMIT 100
"""
)

# Convert results to JSON format
sparql.setReturnFormat(JSON)
result = sparql.query().convert()

# The return data contains "bindings" (a list of dictionaries)
for hit in result["results"]["bindings"]:
    # We want the "value" attribute of the "comment" field
    print(hit["comment"]["value"])
