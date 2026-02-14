# -*- coding: utf-8 -*-
import os
from typing import Dict


class KuaishouGraphQL:
    def __init__(self):
        self.graphql_queries: Dict[str, str] = {}
        self.graphql_dir = os.path.join(os.path.dirname(__file__), "graphql")
        self.load_graphql_queries()

    def load_graphql_queries(self):
        """
        加载GraphQL查询文件
        """
        graphql_files = [
            "vision_profile.graphql",
            "vision_profile_photo_list.graphql", 
            "video_detail.graphql",
            "vision_profile_user_list.graphql",
        ]

        for file in graphql_files:
            file_path = os.path.join(self.graphql_dir, file)
            if os.path.exists(file_path):
                try:
                    with open(file_path, mode="r", encoding="utf-8") as f:
                        query_name = file.split(".")[0]
                        self.graphql_queries[query_name] = f.read()
                except Exception as e:
                    from pkg.tools import utils
                    utils.logger.error(f"Error loading GraphQL file {file}: {e}")
            else:
                from pkg.tools import utils
                utils.logger.warning(f"GraphQL file not found: {file_path}")

    def get(self, query_name: str) -> str:
        """
        获取GraphQL查询语句
        
        Args:
            query_name: 查询名称
            
        Returns:
            str: GraphQL查询语句
        """
        return self.graphql_queries.get(query_name, "Query not found")