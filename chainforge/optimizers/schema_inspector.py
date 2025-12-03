"""Utility script to inspect Memgraph schema for prompt taxonomy."""
from neo4j import GraphDatabase


def inspect_memgraph_schema(uri="bolt://localhost:7688", user="", password=""):
    """
    Connect to Memgraph and inspect the graph schema.

    Args:
        uri: Memgraph connection URI
        user: Username (empty for Memgraph default)
        password: Password (empty for Memgraph default)
    """
    try:
        # Memgraph typically doesn't require auth
        if user and password:
            driver = GraphDatabase.driver(uri, auth=(user, password))
        else:
            driver = GraphDatabase.driver(uri, auth=None)

        with driver.session() as session:
            # Get all node labels
            print("=== Node Labels ===")

            # First check if there are any nodes at all
            count_result = session.run("MATCH (n) RETURN count(n) as count")
            count_record = count_result.single()
            if count_record:
                node_count = count_record["count"]
                print(f"Total nodes in database: {node_count}")

                if node_count == 0:
                    print("  Database is empty. No nodes found.")
                    driver.close()
                    return
            else:
                print("  Could not query database.")
                driver.close()
                return

            # Now get labels
            result = session.run("""
                MATCH (n)
                RETURN DISTINCT labels(n) AS labelList
            """)

            labels = []
            for record in result:
                label_list = record["labelList"]
                if label_list:  # labelList is an array
                    labels.extend(label_list)

            labels = list(set(labels))  # Remove duplicates

            if not labels:
                print("  No labels found. Database might be empty.")
            else:
                for label in labels:
                    print(f"  - {label}")

            print("\n=== Relationship Types ===")
            result = session.run("""
                MATCH ()-[r]->()
                RETURN DISTINCT type(r) AS rel_type
            """)
            rel_types = [record["rel_type"] for record in result]

            if not rel_types:
                print("  No relationships found.")
            else:
                for rel_type in rel_types:
                    print(f"  - {rel_type}")

            # Get sample nodes and their properties for each label
            if labels:
                print("\n=== Sample Nodes and Properties ===")
                for label in labels:
                    print(f"\n{label} nodes:")
                    query = "MATCH (n:" + label + ") RETURN n LIMIT 3"
                    result = session.run(query)
                    count = 0
                    for record in result:
                        node = record["n"]
                        print(f"  Properties: {dict(node)}")
                        count += 1
                    if count == 0:
                        print(f"  No {label} nodes found.")

            # Get relationship patterns
            if rel_types:
                print("\n=== Relationship Patterns ===")
                result = session.run("""
                    MATCH (a)-[r]->(b)
                    RETURN DISTINCT labels(a) as from_labels, type(r) as rel_type, labels(b) as to_labels
                    LIMIT 20
                """)
                pattern_count = 0
                for record in result:
                    from_labels = record["from_labels"]
                    rel_type = record["rel_type"]
                    to_labels = record["to_labels"]
                    print(f"  ({':'.join(from_labels)})-[{rel_type}]->({':'.join(to_labels)})")
                    pattern_count += 1
                if pattern_count == 0:
                    print("  No relationship patterns found.")

            # Count nodes by label
            if labels:
                print("\n=== Node Counts ===")
                for label in labels:
                    query = "MATCH (n:" + label + ") RETURN count(n) as count"
                    result = session.run(query)
                    record = result.single()
                    if record:
                        count = record["count"]
                        print(f"  {label}: {count} nodes")
                    else:
                        print(f"  {label}: 0 nodes")

        driver.close()

    except Exception as e:
        print(f"Error connecting to Memgraph: {e}")
        print("\nMake sure Memgraph is running at localhost:7688")
        print("You can start it with: docker run -p 7688:7687 memgraph/memgraph")


if __name__ == "__main__":
    print("Inspecting Memgraph Schema at localhost:7688\n")
    inspect_memgraph_schema()
