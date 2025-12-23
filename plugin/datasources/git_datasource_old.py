"""
Git Datasource - WebsiteCrawlDatasource implementation.

GATE TEST VERSION: Returns 1 test file to validate Dify semantics.
"""

from collections.abc import Generator
from typing import Any

from dify_plugin.entities.datasource import (
    DatasourceMessage,
    WebSiteInfo,
    WebSiteInfoDetail,
)
from dify_plugin.interfaces.datasource.website import WebsiteCrawlDatasource


class GitDataSource(WebsiteCrawlDatasource):
    """
    Git Repository Data Source using website_crawl interface.
    
    GATE TEST: This is a minimal implementation to validate Dify sync semantics.
    """

    def _get_website_crawl(
        self, 
        datasource_parameters: dict[str, Any]
    ) -> Generator[DatasourceMessage, None, None]:
        """
        GATE TEST: Return test files to validate Dify semantics.
        
        Test plan:
        1. First sync: return 2 files (test1.md, test2.md)
        2. Second sync: return only 1 file (test1.md modified)
        3. Check if test2.md becomes orphaned or stays
        
        If test2.md becomes orphaned -> Dify uses snapshot-diff (need full sync)
        If test2.md stays -> Dify uses upsert-only (delta model works)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Log parameters for debugging
        logger.info(f"datasource_parameters: {datasource_parameters}")
        logger.info(f"credentials keys: {list(self.runtime.credentials.keys())}")
        
        # Get parameters from datasource_parameters (not credentials!)
        repo_url = datasource_parameters.get("repo_url", "unknown")
        branch = datasource_parameters.get("branch", "main") or "main"
        subdir = datasource_parameters.get("subdir", "")
        extensions = datasource_parameters.get("extensions", "")
        
        logger.info(f"repo_url={repo_url}, branch={branch}, subdir={subdir}, extensions={extensions}")
        
        # Check sync counter in storage to alternate behavior
        counter_key = "gate_test_counter"
        counter = 0
        if self.session.storage.exist(counter_key):
            counter = int(self.session.storage.get(counter_key).decode("utf-8"))
        
        # Increment counter
        self.session.storage.set(counter_key, str(counter + 1).encode("utf-8"))
        
        files = []
        
        if counter == 0:
            # First sync: return 2 files
            files = [
                WebSiteInfoDetail(
                    title="test1.md",
                    content="# Test File 1\n\nThis is test file 1 content.",
                    source_url="git:gate_test:test1.md",
                    description=f"Git: {repo_url} @ {branch}",
                ),
                WebSiteInfoDetail(
                    title="test2.md",
                    content="# Test File 2\n\nThis is test file 2 content.",
                    source_url="git:gate_test:test2.md",
                    description=f"Git: {repo_url} @ {branch}",
                ),
            ]
            logger.info(f"First sync: returning {len(files)} files")
        else:
            # Subsequent syncs: return only 1 file (modified)
            files = [
                WebSiteInfoDetail(
                    title="test1.md",
                    content=f"# Test File 1 (Modified)\n\nSync #{counter + 1}",
                    source_url="git:gate_test:test1.md",
                    description=f"Git: {repo_url} @ {branch}",
                ),
            ]
            logger.info(f"Delta sync #{counter + 1}: returning {len(files)} file(s)")
        
        yield self.create_crawl_message(
            WebSiteInfo(
                web_info_list=files,
                status="completed",
                total=len(files),
                completed=len(files),
            )
        )
