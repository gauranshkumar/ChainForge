"""Test script for Memgraph query functionality."""
import sys
from typing import Dict, Any


def test_memgraph_connection(uri="bolt://localhost:7688", user="", password=""):
    """Test connection to Memgraph and query Pattern nodes."""
    try:
        from neo4j import GraphDatabase

        print(f"Connecting to Memgraph at {uri}...")

        # Connect (Memgraph typically doesn't require auth)
        if user and password:
            driver = GraphDatabase.driver(uri, auth=(user, password))
        else:
            driver = GraphDatabase.driver(uri, auth=None)

        with driver.session() as session:
            print("✓ Connected successfully!\n")

            # Test 1: Count Pattern nodes
            print("=== Test 1: Count Pattern nodes ===")
            result = session.run("MATCH (p:Pattern) RETURN count(p) as count")
            count = result.single()["count"]
            print(f"Total Pattern nodes: {count}\n")

            # Test 2: Sample Pattern nodes with labels
            print("=== Test 2: Sample Pattern nodes ===")
            result = session.run("""
                MATCH (p:Pattern)
                WHERE p.label IS NOT NULL
                RETURN p.label as template
                LIMIT 5
            """)
            for i, record in enumerate(result, 1):
                template = record["template"]
                print(f"{i}. {template}")
            print()

            # Test 3: Pattern → SubCategory → Category structure
            print("=== Test 3: Pattern relationships ===")
            result = session.run("""
                MATCH (p:Pattern)-[:BELONGS_TO]->(sc:SubCategory)
                OPTIONAL MATCH (sc)-[:BELONGS_TO]->(c:Category)
                RETURN p.label as pattern, sc.name as subcategory, c.name as category
                LIMIT 5
            """)
            for record in result:
                pattern = record.get("pattern", "N/A")
                subcategory = record.get("subcategory", "N/A")
                category = record.get("category", "N/A")
                print(f"Pattern: {pattern[:50]}...")
                print(f"  → SubCategory: {subcategory}")
                print(f"  → Category: {category}\n")

            # Test 4: Patterns from different subcategories
            print("=== Test 4: Fetch patterns from different subcategories ===")
            # First, get a sample subcategory
            result = session.run("""
                MATCH (p:Pattern)-[:BELONGS_TO]->(sc:SubCategory)
                RETURN sc.name as subcategory
                LIMIT 1
            """)
            sample_record = result.single()
            if sample_record:
                sample_subcategory = sample_record["subcategory"]
                print(f"Reference SubCategory: {sample_subcategory}")

                # Now fetch patterns from different subcategories
                result = session.run("""
                    MATCH (p:Pattern)-[:BELONGS_TO]->(sc:SubCategory)
                    WHERE sc.name <> $current_subcategory AND p.label IS NOT NULL
                    RETURN DISTINCT p.label as template, sc.name as subcategory
                    LIMIT 5
                """, current_subcategory=sample_subcategory)

                print(f"\nPatterns from OTHER subcategories:")
                for record in result:
                    template = record["template"]
                    subcategory = record["subcategory"]
                    print(f"  [{subcategory}] {template[:60]}...")
            print()

            # Test 5: Patterns from different categories
            print("=== Test 5: Fetch patterns from different categories ===")
            result = session.run("""
                MATCH (p:Pattern)-[:BELONGS_TO*1..2]->(c:Category)
                RETURN c.name as category
                LIMIT 1
            """)
            sample_record = result.single()
            if sample_record:
                sample_category = sample_record["category"]
                print(f"Reference Category: {sample_category}")

                # Fetch patterns from different categories
                result = session.run("""
                    MATCH (p:Pattern)-[:BELONGS_TO*1..2]->(c:Category)
                    WHERE c.name <> $current_category AND p.label IS NOT NULL
                    RETURN DISTINCT p.label as template, c.name as category
                    LIMIT 5
                """, current_category=sample_category)

                print(f"\nPatterns from OTHER categories:")
                for record in result:
                    template = record["template"]
                    category = record["category"]
                    print(f"  [{category}] {template[:60]}...")

            print("\n✓ All tests completed successfully!")

        driver.close()

    except ImportError:
        print("ERROR: neo4j package not installed!")
        print("Install it with: pip install neo4j")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("Testing Memgraph Query Functionality\n")
    print("=" * 60)
    test_memgraph_connection()
