# Changelog

## [0.6.0](https://github.com/liottandrea/ust_coding_agent/compare/deepagents==0.5.5...deepagents==0.6.0) (2026-04-30)


### ⚠ BREAKING CHANGES

* **quickjs:** use quickjs-rs ([#2977](https://github.com/liottandrea/ust_coding_agent/issues/2977))

### Features

* **harbor,sdk:** migrate LangSmith env from templates to snapshots ([#2888](https://github.com/liottandrea/ust_coding_agent/issues/2888)) ([082b900](https://github.com/liottandrea/ust_coding_agent/commit/082b9008d14882be83a437d0c1155005e2f1e722))
* **quickjs:** use quickjs-rs ([#2977](https://github.com/liottandrea/ust_coding_agent/issues/2977)) ([34f30ad](https://github.com/liottandrea/ust_coding_agent/commit/34f30ad7053c17a71a1b387780f4838c52aca63a))
* **sdk,cli:** add openrouter SDK attribution ([#2205](https://github.com/liottandrea/ust_coding_agent/issues/2205)) ([2798e51](https://github.com/liottandrea/ust_coding_agent/commit/2798e51fd90128ffd1a2064383db17c699805395))
* **sdk:** `BASE_AGENT_PROMPT` tweaks ([#2541](https://github.com/liottandrea/ust_coding_agent/issues/2541)) ([812eef1](https://github.com/liottandrea/ust_coding_agent/commit/812eef185ffda7bc9e6f11425eb5eddc3d3b32e8))
* **sdk:** `ls_agent_type` configurable tag on subagent runs ([#2788](https://github.com/liottandrea/ust_coding_agent/issues/2788)) ([3bcc51a](https://github.com/liottandrea/ust_coding_agent/commit/3bcc51a95da80094cfc8bc4bcaf25dc1e2ad8f44))
* **sdk:** add `artifacts_root` to `CompositeBackend` and middleware ([#2490](https://github.com/liottandrea/ust_coding_agent/issues/2490)) ([753ee56](https://github.com/liottandrea/ust_coding_agent/commit/753ee567f1cc4d544dc2afea7b414564fd07d37d))
* **sdk:** add optional module field to skill frontmatter ([#2976](https://github.com/liottandrea/ust_coding_agent/issues/2976)) ([2a9cd44](https://github.com/liottandrea/ust_coding_agent/commit/2a9cd44f61c6c15bf74c63dff0f3478cdee18d11))
* **sdk:** add permissions system for filesystem access control ([#2633](https://github.com/liottandrea/ust_coding_agent/issues/2633)) ([41dc759](https://github.com/liottandrea/ust_coding_agent/commit/41dc7597deb3fc036f1f850e68edc3c0870f27da))
* **sdk:** add static structured output to subagent response ([#2437](https://github.com/liottandrea/ust_coding_agent/issues/2437)) ([6e57731](https://github.com/liottandrea/ust_coding_agent/commit/6e57731fc6d908ac1ebe131e782696a4776147e9))
* **sdk:** deprecate `model=None` in `create_deep_agent` ([#2677](https://github.com/liottandrea/ust_coding_agent/issues/2677)) ([149df41](https://github.com/liottandrea/ust_coding_agent/commit/149df415d17f3cf3b7eb0bd1e78460112bfa9b04))
* **sdk:** evict large HumanMessages ([#2183](https://github.com/liottandrea/ust_coding_agent/issues/2183)) ([4f72c34](https://github.com/liottandrea/ust_coding_agent/commit/4f72c34221aea0516738be566de0fffc2c7386ac))
* **sdk:** namespace improvements for deepagents ([#2386](https://github.com/liottandrea/ust_coding_agent/issues/2386)) ([66c57e1](https://github.com/liottandrea/ust_coding_agent/commit/66c57e1e33e21d5ed0b7ceaa615b0e1c27ac556b))
* **sdk:** scope permissions to routes for composite backends with sandbox default ([#2659](https://github.com/liottandrea/ust_coding_agent/issues/2659)) ([6dd6122](https://github.com/liottandrea/ust_coding_agent/commit/6dd612237a7ee707726c4cafc4b691704e4cdb37))


### Bug Fixes

* **cli:** prevent stdin hang by passing `DEVNULL` ([#2427](https://github.com/liottandrea/ust_coding_agent/issues/2427)) ([5bf5fae](https://github.com/liottandrea/ust_coding_agent/commit/5bf5fae8d93beba90628f2f71e3e79817a36ac9e))
* **deepagents:** remove old integration tests ([#2728](https://github.com/liottandrea/ust_coding_agent/issues/2728)) ([6653197](https://github.com/liottandrea/ust_coding_agent/commit/6653197b6cbec6dd1ca23d9f90bc1439ca26e6e5))
* plumb through generics for `create_deep_agent` ([#2383](https://github.com/liottandrea/ust_coding_agent/issues/2383)) ([6c28e22](https://github.com/liottandrea/ust_coding_agent/commit/6c28e22cc5768a82b27102adcea4dbb4b5ae6213))
* remove legacy subagents API ([#2443](https://github.com/liottandrea/ust_coding_agent/issues/2443)) ([56bbfd3](https://github.com/liottandrea/ust_coding_agent/commit/56bbfd3a7c9fc993f7ea6c54d5c54fca234c2273))
* **sdk,cli:** align error messages and clean up recent refactors ([#2171](https://github.com/liottandrea/ust_coding_agent/issues/2171)) ([e2db737](https://github.com/liottandrea/ust_coding_agent/commit/e2db73779926e1effd6d227e14b137b93393461e))
* **sdk:** `last_updated_at` field doesn't account for task status changes ([#2370](https://github.com/liottandrea/ust_coding_agent/issues/2370)) ([8e1a2d6](https://github.com/liottandrea/ust_coding_agent/commit/8e1a2d671eda3903d9ebacca4a5e4aa7378646c2))
* **sdk:** add new line after HEREDOC for edit inline sandbox ([#2340](https://github.com/liottandrea/ust_coding_agent/issues/2340)) ([beb4dbb](https://github.com/liottandrea/ust_coding_agent/commit/beb4dbb6c75700c6969f2c3bfe8f7bf6046ef3bb))
* **sdk:** bump recursion limit to 10_000 in deepagents and set agent name ([#2194](https://github.com/liottandrea/ust_coding_agent/issues/2194)) ([7dbc251](https://github.com/liottandrea/ust_coding_agent/commit/7dbc25180e05261fba4d5ec752d3052fbc826e4c))
* **sdk:** catch `UnicodeDecodeError` in `FilesystemBackend.read` ([#2319](https://github.com/liottandrea/ust_coding_agent/issues/2319)) ([9783fe4](https://github.com/liottandrea/ust_coding_agent/commit/9783fe43b71ad0fbe30593a263a27f38c6bf8f55))
* **sdk:** catch PermissionError in FilesystemBackend ripgrep ([#2571](https://github.com/liottandrea/ust_coding_agent/issues/2571)) ([3d5d673](https://github.com/liottandrea/ust_coding_agent/commit/3d5d67349c8e88e33af98137db9634742f018cb0))
* **sdk:** fix offloading for state backend ([#2266](https://github.com/liottandrea/ust_coding_agent/issues/2266)) ([92f5507](https://github.com/liottandrea/ust_coding_agent/commit/92f55075d978c27a6aa658968a1999754af973fe))
* **sdk:** fix TypeError in async sub-agents ([#2376](https://github.com/liottandrea/ust_coding_agent/issues/2376)) ([8be4a2e](https://github.com/liottandrea/ust_coding_agent/commit/8be4a2ee3878a3e15c15d56fd64ba8db248a6328))
* **sdk:** harden `FilesystemBackend` against symlink loops ([#3035](https://github.com/liottandrea/ust_coding_agent/issues/3035)) ([abd02f9](https://github.com/liottandrea/ust_coding_agent/commit/abd02f99ef12030bdfe429fdc3ad80a2785bea61))
* **sdk:** implement upload_files for StateBackend ([#2661](https://github.com/liottandrea/ust_coding_agent/issues/2661)) ([5798345](https://github.com/liottandrea/ust_coding_agent/commit/579834513a4ba1a024a52fc4edf918f526eab5f2))
* **sdk:** improvements in default sandbox.write and sandbox.read implementations ([#2321](https://github.com/liottandrea/ust_coding_agent/issues/2321)) ([4a37a46](https://github.com/liottandrea/ust_coding_agent/commit/4a37a469ffd8a2d3b515c4de72674673f433082b))
* **sdk:** inherit parent `interrupt_on` for subagents ([#2334](https://github.com/liottandrea/ust_coding_agent/issues/2334)) ([acad9bb](https://github.com/liottandrea/ust_coding_agent/commit/acad9bb6ceebee7dc74bd75dcffa49faa8697658))
* **sdk:** make created_at and modified_at NotRequired fields on FileData ([#2248](https://github.com/liottandrea/ust_coding_agent/issues/2248)) ([9862b5a](https://github.com/liottandrea/ust_coding_agent/commit/9862b5ad0e94fa52fde6971ac9c2a0a1875ee451))
* **sdk:** match example_agent_descriptions closing tag in task tool prompt ([#2462](https://github.com/liottandrea/ust_coding_agent/issues/2462)) ([c36a41c](https://github.com/liottandrea/ust_coding_agent/commit/c36a41ccacd46d54806943821ebf16c606a5bc9f))
* **sdk:** normalize CRLF line endings in `FilesystemBackend.edit()` ([#2256](https://github.com/liottandrea/ust_coding_agent/issues/2256)) ([69bd21e](https://github.com/liottandrea/ust_coding_agent/commit/69bd21e2b14fa4bfd88d858702aff0e64237d35d))
* **sdk:** normalize Windows backslash paths before PurePosixPath processing ([#1859](https://github.com/liottandrea/ust_coding_agent/issues/1859)) ([e1c1d50](https://github.com/liottandrea/ust_coding_agent/commit/e1c1d5024729f5205eaa42bf6a9bc1c93a30d043))
* **sdk:** preserve CRLF line endings in sandbox edit ([#2899](https://github.com/liottandrea/ust_coding_agent/issues/2899)) ([291aebe](https://github.com/liottandrea/ust_coding_agent/commit/291aebe21f8a53604a2bf47daa120761dace2536))
* **sdk:** raise `ValueError` for permission paths without leading slash and path traversal ([#2665](https://github.com/liottandrea/ust_coding_agent/issues/2665)) ([723d27d](https://github.com/liottandrea/ust_coding_agent/commit/723d27dcdce03cc9ffaa757c70533f0134a43a44))
* **sdk:** re-export filesystem permission for backwards compatibility ([#3036](https://github.com/liottandrea/ust_coding_agent/issues/3036)) ([e04b50a](https://github.com/liottandrea/ust_coding_agent/commit/e04b50ae291abefa64ee2750a0c1bbfd93954b32))
* **sdk:** restore deprecated protocol return types ([#2342](https://github.com/liottandrea/ust_coding_agent/issues/2342)) ([845cdf5](https://github.com/liottandrea/ust_coding_agent/commit/845cdf52d7f15ab2b260de95f8448c04264c1efc))
* **sdk:** route subagent model resolution to `resolve_model` ([#2208](https://github.com/liottandrea/ust_coding_agent/issues/2208)) ([6720e4c](https://github.com/liottandrea/ust_coding_agent/commit/6720e4c520295ac1cb24c19cf3d315d2d05ba257))
* **sdk:** skill loading should default to 1000 lines ([#2721](https://github.com/liottandrea/ust_coding_agent/issues/2721)) ([badc4d3](https://github.com/liottandrea/ust_coding_agent/commit/badc4d3921ae0ede4305f44f85fa7266df9465e7))
* **sdk:** support read-your-writes in StateBackend ([#2991](https://github.com/liottandrea/ust_coding_agent/issues/2991)) ([0924869](https://github.com/liottandrea/ust_coding_agent/commit/0924869bc3d946577e7c3cbc79a86e4aaf522edd))
* **sdk:** surface EOF-newline mismatch in `edit_file` ([#3031](https://github.com/liottandrea/ust_coding_agent/issues/3031)) ([d30686e](https://github.com/liottandrea/ust_coding_agent/commit/d30686ec82d36a0e9430f7c512c34835aba2c079))
* **sdk:** treat boundary-truncated UTF-8 in `read()` prefix check as text ([#2980](https://github.com/liottandrea/ust_coding_agent/issues/2980)) ([c36ebc7](https://github.com/liottandrea/ust_coding_agent/commit/c36ebc7be5840e9008279992741c67a8377ffc01))
* **sdk:** update recursion limit ([#2273](https://github.com/liottandrea/ust_coding_agent/issues/2273)) ([fd91a30](https://github.com/liottandrea/ust_coding_agent/commit/fd91a30bf394d4d0ebf8deed9e7835dfc05c9891))
* **sdk:** updates for multimodal ([#2514](https://github.com/liottandrea/ust_coding_agent/issues/2514)) ([a2edf3e](https://github.com/liottandrea/ust_coding_agent/commit/a2edf3ed80e17a87027c41a46283387031ebd3e5))
* **sdk:** Use configurable directly instead of tracing context for subagent tagging ([#2845](https://github.com/liottandrea/ust_coding_agent/issues/2845)) ([bd6ec6b](https://github.com/liottandrea/ust_coding_agent/commit/bd6ec6bcebcdcc26f6b79e2c55611074b0e01631))


### Performance Improvements

* **sdk:** add cache breakpoint to `MemoryMiddleware` ([#2713](https://github.com/liottandrea/ust_coding_agent/issues/2713)) ([1699f3a](https://github.com/liottandrea/ust_coding_agent/commit/1699f3aea710985087b16318bb8e6f6e80e02a1b))

## [0.5.5](https://github.com/langchain-ai/deepagents/compare/deepagents==0.5.4...deepagents==0.5.5) (2026-04-30)

### Bug Fixes

* Harden `FilesystemBackend` against symlink loops ([#3035](https://github.com/langchain-ai/deepagents/issues/3035)) ([abd02f9](https://github.com/langchain-ai/deepagents/commit/abd02f99ef12030bdfe429fdc3ad80a2785bea61))
* Surface EOF-newline mismatch in `edit_file` ([#3031](https://github.com/langchain-ai/deepagents/issues/3031)) ([d30686e](https://github.com/langchain-ai/deepagents/commit/d30686ec82d36a0e9430f7c512c34835aba2c079))
* Prevent stdin hang by passing `DEVNULL` ([#2427](https://github.com/langchain-ai/deepagents/issues/2427)) ([5bf5fae](https://github.com/langchain-ai/deepagents/commit/5bf5fae8d93beba90628f2f71e3e79817a36ac9e))

## [0.5.4](https://github.com/langchain-ai/deepagents/compare/deepagents==0.5.3...deepagents==0.5.4) (2026-04-29)

### Highlights

Until this release, `deepagents` shipped a single set of prompts, tools, and middleware tuned to work across *all* model families. Today's headline change is **harness profiles** — a declarative override layer for the parts of the harness that vary per model (system-prompt prefix/suffix, tool inclusion and naming, middleware selection, subagent configuration, skills). `ProviderProfile` shapes how `resolve_model` builds the client; `HarnessProfile` / `HarnessProfileConfig` shape how `create_deep_agent` assembles the agent. Both are keyed by provider (`"openai"`) or full `provider:model` spec (`"openai:gpt-5.4"`), and registrations are additive — your call site doesn't change when you swap models.

We currently ship built-ins for OpenAI and Anthropic out of the box, drawn directly from each vendor's published prompting guides (Codex's `apply_patch` / `shell_command` conventions, Claude's tool-result reflection and active-investigation patterns, etc.). On a curated tau2-bench subset, applying these profiles produced a 10–20 point lift over the default harness (GPT-5.3 Codex: 33% -> 53%; Claude Opus 4.7: 43% -> 53%). Third-party plugins can register via the `deepagents.provider_profiles` and `deepagents.harness_profiles` entry points.

See the [profiles documentation](https://docs.langchain.com/oss/python/deepagents/profiles) for the full field surface, merge semantics, and plugin packaging.

### Features

* Profiles API ([#2892](https://github.com/langchain-ai/deepagents/issues/2892)) ([7365ad1](https://github.com/langchain-ai/deepagents/commit/7365ad1600064eec616c5de970320104189ddf80))
* `ls_agent_type` configurable tag on subagent runs ([#2788](https://github.com/langchain-ai/deepagents/issues/2788)) ([3bcc51a](https://github.com/langchain-ai/deepagents/commit/3bcc51a95da80094cfc8bc4bcaf25dc1e2ad8f44))

### Bug Fixes

* Normalize Windows backslash paths before `PurePosixPath` processing ([#1859](https://github.com/langchain-ai/deepagents/issues/1859)) ([e1c1d50](https://github.com/langchain-ai/deepagents/commit/e1c1d5024729f5205eaa42bf6a9bc1c93a30d043))
* Preserve CRLF line endings in sandbox edit ([#2899](https://github.com/langchain-ai/deepagents/issues/2899)) ([291aebe](https://github.com/langchain-ai/deepagents/commit/291aebe21f8a53604a2bf47daa120761dace2536))
* Support read-your-writes in `StateBackend` ([#2991](https://github.com/langchain-ai/deepagents/issues/2991)) ([0924869](https://github.com/langchain-ai/deepagents/commit/0924869bc3d946577e7c3cbc79a86e4aaf522edd))
* Treat boundary-truncated UTF-8 in `read()` prefix check as text ([#2980](https://github.com/langchain-ai/deepagents/issues/2980)) ([c36ebc7](https://github.com/langchain-ai/deepagents/commit/c36ebc7be5840e9008279992741c67a8377ffc01))
* Use `configurable` directly instead of tracing context for subagent tagging ([#2845](https://github.com/langchain-ai/deepagents/issues/2845)) ([bd6ec6b](https://github.com/langchain-ai/deepagents/commit/bd6ec6bcebcdcc26f6b79e2c55611074b0e01631))

### Performance Improvements

* Add cache breakpoint to `MemoryMiddleware` ([#2713](https://github.com/langchain-ai/deepagents/issues/2713)) ([1699f3a](https://github.com/langchain-ai/deepagents/commit/1699f3aea710985087b16318bb8e6f6e80e02a1b))

## [0.5.3](https://github.com/langchain-ai/deepagents/compare/deepagents==0.5.2...deepagents==0.5.3) (2026-04-14)

### Features

* **sdk:** add static structured output to subagent response ([#2437](https://github.com/langchain-ai/deepagents/issues/2437)) ([6e57731](https://github.com/langchain-ai/deepagents/commit/6e57731fc6d908ac1ebe131e782696a4776147e9))
* **sdk:** deprecate `model=None` in `create_deep_agent` ([#2677](https://github.com/langchain-ai/deepagents/issues/2677)) ([149df41](https://github.com/langchain-ai/deepagents/commit/149df415d17f3cf3b7eb0bd1e78460112bfa9b04))

### Bug Fixes

* **sdk:** skill loading should default to 1000 lines ([#2721](https://github.com/langchain-ai/deepagents/issues/2721)) ([badc4d3](https://github.com/langchain-ai/deepagents/commit/badc4d3921ae0ede4305f44f85fa7266df9465e7))

## [0.5.2](https://github.com/langchain-ai/deepagents/compare/deepagents==0.5.1...deepagents==0.5.2) (2026-04-10)

### Features

* Permissions system for filesystem access control ([#2633](https://github.com/langchain-ai/deepagents/issues/2633)) ([41dc759](https://github.com/langchain-ai/deepagents/commit/41dc7597deb3fc036f1f850e68edc3c0870f27da))
  * Scope permissions to routes for composite backends with sandbox default ([#2659](https://github.com/langchain-ai/deepagents/issues/2659)) ([6dd6122](https://github.com/langchain-ai/deepagents/commit/6dd612237a7ee707726c4cafc4b691704e4cdb37))
  * Raise `ValueError` for permission paths without leading slash and path traversal ([#2665](https://github.com/langchain-ai/deepagents/issues/2665)) ([723d27d](https://github.com/langchain-ai/deepagents/commit/723d27dcdce03cc9ffaa757c70533f0134a43a44))
* Implement `upload_files` for `StateBackend` ([#2661](https://github.com/langchain-ai/deepagents/issues/2661)) ([5798345](https://github.com/langchain-ai/deepagents/commit/579834513a4ba1a024a52fc4edf918f526eab5f2))

### Bug Fixes

* Catch `PermissionError` in `FilesystemBackend` ripgrep ([#2571](https://github.com/langchain-ai/deepagents/issues/2571)) ([3d5d673](https://github.com/langchain-ai/deepagents/commit/3d5d67349c8e88e33af98137db9634742f018cb0))

## [0.5.1](https://github.com/langchain-ai/deepagents/compare/deepagents==0.5.0...deepagents==0.5.1) (2026-04-07)

### Features

* **sdk:** `BASE_AGENT_PROMPT` tweaks ([#2541](https://github.com/langchain-ai/deepagents/issues/2541)) ([812eef1](https://github.com/langchain-ai/deepagents/commit/812eef185ffda7bc9e6f11425eb5eddc3d3b32e8))
* **sdk:** add `artifacts_root` to `CompositeBackend` and middleware ([#2490](https://github.com/langchain-ai/deepagents/issues/2490)) ([753ee56](https://github.com/langchain-ai/deepagents/commit/753ee567f1cc4d544dc2afea7b414564fd07d37d))

### Bug Fixes

* **sdk:** updates for multimodal ([#2514](https://github.com/langchain-ai/deepagents/issues/2514)) ([a2edf3e](https://github.com/langchain-ai/deepagents/commit/a2edf3ed80e17a87027c41a46283387031ebd3e5))

---

# Prior Releases

Versions prior to 0.5.1 were released without release-please and do not have changelog entries. Refer to the [releases page](https://github.com/langchain-ai/deepagents/releases?q=deepagents) for details on previous versions.
