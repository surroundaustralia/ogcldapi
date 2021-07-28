from string import Template

# template query to obtain class label for features, to construct a generic title for features where one is not present
# in the data. For example to construct "Mesh Block 12345".
# The query obtains the label for the furthest subclass of geo:Feature present for this feature.
# e.g. if a Mesh Block has the hierarchy: Mesh Block > Structure > ASGS Feature > geo:Feature, then the label for Mesh
# Block will be obtained.
# Utilised in feature.py and features.py
feature_class_label_sparql = Template("""
    PREFIX geo: <http://www.opengis.net/ont/geosparql#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dcterms: <http://purl.org/dc/terms/> 
    SELECT ?entire_label ?label { 
    select ?entire_label ?super ?sub (count(?mid) as ?distance) ?identifier ?label {
      BIND(geo:Feature as ?super)
       <$URI> a ?sub ;
                    dcterms:identifier ?identifier .
        ?sub rdfs:subClassOf* ?mid .
        ?mid rdfs:subClassOf* ?super .
        ?sub rdfs:label ?label .
        BIND((CONCAT(?label," ", ?identifier)) as ?entire_label) 
    }
    group by ?super ?sub ?identifier ?entire_label ?label
    order by DESC(?distance)
    LIMIT 1
    }
    """)