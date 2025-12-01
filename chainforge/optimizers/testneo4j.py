import neo4j 
from neo4j import GraphDatabase

with GraphDatabase.driver("bolt://localhost:7688", auth=("", "")) as driver:
    driver.verify_connectivity()
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) AS node_count")
        record = result.single()
        print(f"Total number of nodes in the database: {record['node_count']}")
