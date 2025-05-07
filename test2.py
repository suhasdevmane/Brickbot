from SPARQLWrapper import SPARQLWrapper, JSON

sparql = SPARQLWrapper("http://localhost:3030/#/dataset/ds/query")
sparql.setReturnFormat(JSON)

# gets the first 3 geological ages
# from a Geological Timescale database,
# via a SPARQL endpoint
sparql.setQuery(
    """
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    PREFIX brk: <http://brk.basisregistraties.overheid.nl/def/brk#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT * WHERE {
        ?sub ?pred ?obj .
    } LIMIT 5
    """
)
# try :
#     ret = sparql.queryAndConvert()

#     for r in ret["results"]["bindings"]:
#         print(r)
# except Exception as e:
#     print(e)
