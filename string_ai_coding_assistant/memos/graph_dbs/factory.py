from typing import Any, ClassVar

from string_ai_coding_assistant.memos.configs.graph_db import GraphDBConfigFactory
from string_ai_coding_assistant.memos.graph_dbs.base import BaseGraphDB
from string_ai_coding_assistant.memos.graph_dbs.neo4j import Neo4jGraphDB


class GraphStoreFactory(BaseGraphDB):
    """Factory for creating graph store instances."""

    backend_to_class: ClassVar[dict[str, Any]] = {
        "neo4j": Neo4jGraphDB,
    }

    @classmethod
    def from_config(cls, config_factory: GraphDBConfigFactory) -> BaseGraphDB:
        backend = config_factory.backend
        if backend not in cls.backend_to_class:
            raise ValueError(f"Unsupported graph database backend: {backend}")
        graph_class = cls.backend_to_class[backend]
        return graph_class(config_factory.config)
