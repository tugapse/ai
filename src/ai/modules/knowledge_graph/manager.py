# src/knowledge_graph_module/manager.py

import json
from typing import Any, List, Dict, Tuple

from ai.modules.knowledge_graph.ast_parser import get_parser
from ai.modules.knowledge_graph.prompts import CODE_EXTRACTION_PROMPT
from ai.modules.knowledge_graph.models import (
    AnalysisReport,
    AmbiguityFlag,
    RefinementReport,
    KGNode,
    KGEdge,
    KGTriple,
    NodeTypes,
    RelationshipTypes
)


class KnowledgeGraphManager:
    """
    Manages the creation, refinement, and querying of the codebase knowledge graph.
    """

    def __init__(self, db_client: Any, llm_client: Any, vectorizer_client: Any):
        """
        Initializes the manager with dependency-injected clients.

        Args:
            db_client: A client for interacting with the graph database.
            llm_client: A client for interacting with the LLM API.
            vectorizer_client: A client for generating embeddings.
        """
        self.db_client = db_client
        self.llm_client = llm_client
        self.vectorizer_client = vectorizer_client

    def update_knowledge_from_files(self, file_paths: List[str]) -> None:
        """
        Orchestrates the end-to-end process of updating the knowledge graph from a list of files.
        (Phase 4 Implementation)
        """
        master_ambiguity_queue: List[AmbiguityFlag] = []
        initial_reports: List[AnalysisReport] = []

        # Phase 1: Initial Analysis of all files
        for file_path in file_paths:
            report = self.analyze_file(file_path)
            if report.status == "success":
                initial_reports.append(report)
                master_ambiguity_queue.extend(report.ambiguity_queue)

                # --- DB Persistence Step 1: Persist initial nodes and triples ---
                if self.db_client:
                    if report.nodes:
                        self.db_client.add_nodes(report.nodes)
                    if report.initial_triples:
                        self.db_client.add_triples(report.initial_triples, is_validated=False, extraction_pass=1)
                
                # A proper logger would be used here.
                print(f"Analyzed {file_path}. Found {len(report.nodes)} nodes, {len(report.initial_triples)} triples, {len(report.ambiguity_queue)} ambiguities.")
            else:
                # Log the error from the report
                print(f"Failed to analyze {file_path}: {report.status}")

        # Phase 2: Global Refinement Loop
        max_refinement_passes = 10 # Safety break to prevent infinite loops
        current_pass = 0
        while master_ambiguity_queue and current_pass < max_refinement_passes:
            current_pass += 1
            print(f"--- Starting Refinement Pass {current_pass} with {len(master_ambiguity_queue)} ambiguities ---")
            
            # Process the current batch of ambiguities
            refinement_report = self.refine_knowledge(master_ambiguity_queue)

            # Update the queue with any unresolved flags
            master_ambiguity_queue = refinement_report.unresolved_flags
            
            print(refinement_report.summary)
            
            # In a real implementation, you might want a delay or a more complex
            # backoff strategy if the queue isn't shrinking.

        if master_ambiguity_queue:
            print(f"Warning: {len(master_ambiguity_queue)} ambiguities remain after {max_refinement_passes} passes.")
        
        # --- DB Persistence Step 2: Finalize validated triples ---
        # After the loop, you could run a final query to update all triples
        # that were successfully resolved to `is_validated=True`.
        if self.db_client:
            self.db_client.mark_resolved_triples_as_validated()
        print("Knowledge graph update process complete.")

    def analyze_file(self, file_path: str) -> AnalysisReport:
        """
        Analyzes a single file to extract initial triples and identify ambiguities.
        (Phase 2 Implementation)
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()

            # The AST-based approach can be a fallback or enrichment layer.
            # For now, we rely on the LLM's ability to parse source code directly.
            # _, ext = os.path.splitext(file_path)
            # language = ext.lstrip('.')
            # if language in ["py", "pyw"]:
            #     language = "python"
            # parser = get_parser(language)
            # ast_tree = parser.parse(source_code)
            # ast_dict = parser.to_dict(ast_tree)

            nodes, initial_triples, ambiguity_queue = self._generate_initial_triples_with_llm(
                file_path=file_path, file_content=source_code
            )

            return AnalysisReport(
                file_path=file_path,
                nodes=nodes,
                initial_triples=initial_triples,
                ambiguity_queue=ambiguity_queue,
                status="success",
            )
        except FileNotFoundError:
            return AnalysisReport(file_path=file_path, status="error_file_not_found")
        except Exception as e:
            # Catch other potential errors during parsing or analysis
            return AnalysisReport(file_path=file_path, status=f"error_analysis_failed: {e}")

    def refine_knowledge(self, ambiguities: List[AmbiguityFlag]) -> RefinementReport:
        """
        Processes a batch of ambiguities to refine the knowledge in the graph.
        (Phase 3 Implementation)
        """
        resolved_triples: List[KGTriple] = []
        unresolved_flags: List[AmbiguityFlag] = []

        # This entire method assumes db_client and llm_client are configured.
        if not self.db_client or not self.llm_client:
            return RefinementReport(
                resolved_triples=[],
                unresolved_flags=ambiguities,
                summary="Refinement skipped: DB or LLM client not configured."
            )

        for flag in ambiguities:
            try:
                # 1. Formulate a KG query to get context for the ambiguous triple.
                # This is a simplified, conceptual query. A real implementation would have
                # specific, structured queries based on the ambiguity type.
                source_id = flag.flagged_triple.source_id
                target_id = flag.flagged_triple.target_id
                query = f"GET_NODE_DETAILS_BY_ID {source_id}, {target_id}"
                query_result = self.db_client.execute_query(query)

                # 2. Construct a refined prompt for the LLM.
                prompt = f"""
                Analyze the following ambiguous knowledge graph triple based on the context from the graph.

                Ambiguity Reason: {flag.reason}
                Suggested Action: {flag.suggested_action}

                Flagged Triple:
                - Source ID: {source_id}
                - Relationship: {flag.flagged_triple.relationship_type.value}
                - Target ID: {target_id}

                Context from Knowledge Graph Query (Results for nodes above):
                {json.dumps(query_result, indent=2)}

                Based on all available information, is this triple resolvable?
                Respond in JSON format with the following keys:
                - "is_resolved": boolean (true if the ambiguity is resolved, false otherwise)
                - "updated_triple": object (optional, if resolved and the triple needs correction)
                    - "relationship_type": string (e.g., "DEFINES", "CALLS")
                - "confidence_score": float (optional, if resolved)
                - "new_reason": string (optional, if not resolved, explain why)
                """

                # 3. Call the LLM for re-evaluation.
                response = self.llm_client.chat.completions.create(
                    model="gpt-4-turbo", # This should be configurable
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": "You are a knowledge graph refinement expert."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                )
                
                response_content = response.choices[0].message.content
                reevaluated_data = json.loads(response_content)

                # 4. Process the response.
                if reevaluated_data.get("is_resolved"):
                    updated_triple_data = reevaluated_data.get("updated_triple")
                    
                    final_triple = KGTriple(
                        source_id=source_id,
                        target_id=target_id,
                        relationship_type=flag.flagged_triple.relationship_type,
                        confidence_score=flag.flagged_triple.confidence_score
                    )

                    if updated_triple_data and "relationship_type" in updated_triple_data:
                        final_triple.relationship_type = RelationshipTypes(updated_triple_data["relationship_type"])
                    
                    if "confidence_score" in reevaluated_data:
                        final_triple.confidence_score = reevaluated_data["confidence_score"]
                    else:
                        final_triple.confidence_score = 1.0
                    
                    resolved_triples.append(final_triple)
                else:
                    if "new_reason" in reevaluated_data:
                        flag.reason = reevaluated_data["new_reason"]
                    unresolved_flags.append(flag)
            
            except Exception as e:
                print(f"Failed to process ambiguity for triple with source {flag.flagged_triple.source_id}: {e}")
                unresolved_flags.append(flag)

        return RefinementReport(
            resolved_triples=resolved_triples,
            unresolved_flags=unresolved_flags,
            summary=f"Processed {len(ambiguities)} ambiguities. {len(resolved_triples)} resolved, {len(unresolved_flags)} remain."
        )

    def query_graph(self, query_type: str, params: Dict[str, Any]) -> List[KGNode | KGEdge]:
        """
        Provides a public interface for querying the knowledge graph.
        (Phase 4 Implementation)
        """
        if not self.db_client:
            print("Warning: DB client not configured. Querying is disabled.")
            return []

        if query_type == "semantic_search":
            if "query_text" not in params or not self.vectorizer_client:
                print("Warning: 'query_text' not in params or vectorizer client not configured for semantic search.")
                return []
            
            try:
                # 1. Embed the query text
                query_embedding = self.vectorizer_client.encode(params["query_text"]).tolist()
                
                # 2. Perform similarity search in the database
                # This assumes the db_client has a method for vector search.
                limit = params.get("limit", 10)
                similar_nodes = self.db_client.find_similar_nodes(query_embedding, limit=limit)
                
                return [KGNode(**node_data) for node_data in similar_nodes]
            except Exception as e:
                print(f"Error during semantic search: {e}")
                return []

        elif query_type == "structural_query":
            if "query" not in params:
                print("Warning: 'query' not in params for structural query.")
                return []
            
            try:
                # Example: A generic structural query handler.
                query_string = params.get("query")
                query_params = params.get("params", {})
                results = self.db_client.execute_query(query_string, query_params)
                
                # Note: The result type (Node or Edge) depends on the query.
                # This is a simplification; a real implementation would need more robust
                # result parsing based on what the query is expected to return.
                return results
            except Exception as e:
                print(f"Error during structural query: {e}")
                return []

        # Return empty list for unknown query types
        print(f"Warning: Unknown query_type '{query_type}'.")
        return []

    def _generate_initial_triples_with_llm(
        self, file_path: str, file_content: str
    ) -> Tuple[List[KGNode], List[KGTriple], List[AmbiguityFlag]]:
        """
        Uses the LLM to generate triples and ambiguity flags from file content.
        (Phase 2 Implementation)
        """
        # In-memory cache to avoid creating duplicate nodes for the same entity within a single file analysis.
        # The key is a tuple of (node_type, node_name).
        node_cache: Dict[Tuple[str, str], KGNode] = {}
        triples: List[KGTriple] = []
        ambiguities: List[AmbiguityFlag] = []

        system_prompt = CODE_EXTRACTION_PROMPT
        # The user prompt includes the file path for context and the full source code.
        user_prompt = f"File Path: `{file_path}`\n\nSource Code:\n```\n{file_content}\n```"

        try:
            # This assumes an OpenAI-compatible client is injected.
            response = self.llm_client.chat.completions.create(
                model="gpt-4-turbo", # This should be configurable
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
            )
            
            response_content = response.choices[0].message.content
            if not response_content:
                # If LLM returns empty content, there's nothing to process.
                return [], [], []

            data = json.loads(response_content)
            raw_triples = data.get("triples", [])

            for raw_triple in raw_triples:
                if not (isinstance(raw_triple, list) and len(raw_triple) == 3):
                    continue  # Skip malformed triples

                source_data, rel_str, target_data = raw_triple
                
                if not (isinstance(source_data, dict) and isinstance(target_data, dict) and "type" in source_data and "name" in source_data):
                    continue # Skip malformed node data

                # --- Process Source Node ---
                source_key = (source_data["type"], source_data["name"])
                if source_key not in node_cache:
                    node_cache[source_key] = KGNode(
                        type=NodeTypes(source_data["type"]),
                        name=source_data["name"],
                        source_text=source_data.get("source_text"),
                        properties={"source_file": file_path},
                    )
                source_node = node_cache[source_key]

                # --- Process Target Node ---
                if not ("type" in target_data and "name" in target_data):
                    continue # Skip malformed node data
                target_key = (target_data["type"], target_data["name"])
                if target_key not in node_cache:
                    node_cache[target_key] = KGNode(
                        type=NodeTypes(target_data["type"]),
                        name=target_data["name"],
                        source_text=target_data.get("source_text"),
                        properties={"source_file": file_path},
                    )
                target_node = node_cache[target_key]

                # --- Create Triple ---
                try:
                    relationship_type = RelationshipTypes(rel_str)
                    triples.append(
                        KGTriple(
                            source_id=source_node.id,
                            relationship_type=relationship_type,
                            target_id=target_node.id,
                            confidence_score=0.9 # Placeholder confidence
                        )
                    )
                except ValueError:
                    # If the LLM returns an invalid relationship type, skip it.
                    pass

        except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as e:
            # A proper logger should be used here.
            print(f"Error processing LLM response for {file_path}: {e}")
            return [], [], []
        except Exception as e:
            # Catch-all for other potential errors (e.g., network issues)
            print(f"An unexpected error occurred during analysis of {file_path}: {e}")
            return [], [], []

        return list(node_cache.values()), triples, ambiguities

    def _create_and_store_embedding(self, node: KGNode) -> None:
        """
        Generates and stores an embedding for a given KGNode.
        (Phase 3 Implementation)
        """
        if not self.vectorizer_client or not self.db_client:
            # Silently skip if clients are not configured, log this in a real app
            return

        # Create a descriptive text from the node for embedding
        text_to_embed = f"Type: {node.type.value}, Name: {node.name}"
        if node.source_text:
            text_to_embed += f", Code: {node.source_text}"

        try:
            # Generate embedding using the injected client
            # Assuming the client has an `encode` method like sentence-transformers
            embedding = self.vectorizer_client.encode(text_to_embed).tolist()

            # Update the node object itself
            node.embedding = embedding
            
            # Persist the embedding to the graph database
            # This assumes the db_client has a method to update a node's properties.
            self.db_client.update_node_properties(
                node_id=node.id,
                properties={"embedding": embedding}
            )

        except Exception as e:
            # A proper logger should be used here.
            print(f"Error generating or storing embedding for node {node.id}: {e}")