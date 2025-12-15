# Reference links (Dify + plugins + Git)

## Dify — plugins overview
- Dify Plugins (entry point): https://docs.dify.ai/plugins
- Develop plugins (entry point): https://docs.dify.ai/en/develop-plugin

## Dify — Data Source plugin docs
- Data Source Plugin (guide): https://docs.dify.ai/en/develop-plugin/dev-guides-and-walkthroughs/datasource-plugin

## Dify — plugin tool & examples (useful as “how to” references)
- Agent Strategy Plugin guide (mentions `dify plugin init` and dev tool prerequisites):  
  https://docs.dify.ai/en/develop-plugin/dev-guides-and-walkthroughs/agent-strategy-plugin
- Develop a Slack Bot Plugin (another end-to-end plugin guide):  
  https://docs.dify.ai/en/develop-plugin/dev-guides-and-walkthroughs/develop-a-slack-bot-plugin

## Dify — schema / SDK
- Dify Plugin SDK Schema Reference: https://langgenius.github.io/dify-plugin-sdks/schema/
- dify-plugin-sdks (GitHub): https://github.com/langgenius/dify-plugin-sdks

## Dify — plugin marketplace & official examples
- Dify plugin marketplace repo: https://github.com/langgenius/dify-plugins
- Dify official plugins (examples across types, incl. datasources): https://github.com/langgenius/dify-official-plugins
- Dify main repo: https://github.com/langgenius/dify

## Python-native Git libraries
(We’ll choose one primary, keep fallbacks in mind.)

- GitPython (wrapper around `git` CLI; pragmatic, but needs `git` binary):
  https://gitpython.readthedocs.io/
- Dulwich (pure-Python Git implementation; good portability):
  https://www.dulwich.io/docs/
- pygit2 (bindings for libgit2; fast, but heavier deps):
  https://www.pygit2.org/
- libgit2 (foundation for pygit2):
  https://libgit2.org/

## Git fundamentals (protocol & semantics)
- Git docs index: https://git-scm.com/docs
- Git Book (background): https://git-scm.com/book/en/v2
- Object naming / revspec / SHAs: https://git-scm.com/docs/gitrevisions
- Diff / name-status / change detection (CLI refs we may emulate):
  - https://git-scm.com/docs/git-diff
  - https://git-scm.com/docs/git-log
  - https://git-scm.com/docs/git-rev-list

## Auth building blocks (likely needed)
- SSH (Python): Paramiko: https://www.paramiko.org/
- HTTPS auth patterns:
  - GitLab personal access tokens (conceptually; internal GitLab likely mirrors this UX)
  - Basic auth over HTTPS (last resort)
