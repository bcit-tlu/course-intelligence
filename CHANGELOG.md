# Changelog

## [0.16.0](https://github.com/bcit-tlu/course-intelligence/compare/backend-v0.15.0...backend-v0.16.0) (2026-08-29)


### Features

* 133 llm provider abstraction ([cbe0263](https://github.com/bcit-tlu/course-intelligence/commit/cbe0263551a363fe4ec4a9853fc54e0abe3a2313))
* add LLM retry logic with exponential backoff and per-call observability ([61aaa4c](https://github.com/bcit-tlu/course-intelligence/commit/61aaa4c6ec0ffb7bf514d590cda14364a0b5792e))
* add LM Studio and OpenAI provider support with centralized LLM factory ([c9c8cad](https://github.com/bcit-tlu/course-intelligence/commit/c9c8cad9e9b9e453d0a66a395d5a2572e76c5668))

## [0.15.0](https://github.com/bcit-tlu/course-intelligence/compare/backend-v0.14.0...backend-v0.15.0) (2026-08-28)


### Features

* display total log count in LevelFilter "All" badge ([a90c5a5](https://github.com/bcit-tlu/course-intelligence/commit/a90c5a5dfedc708eb7651ae2efc86587ab03e93e))


### Bug Fixes

* configure Vite dev server for Docker with dynamic backend URL and disable OTel in dev ([7fef26c](https://github.com/bcit-tlu/course-intelligence/commit/7fef26c10c72a8657b4e319951b12a287a5941d9))
* remove .env.local generation from dev container and auto-detect Docker environment ([e31cf4f](https://github.com/bcit-tlu/course-intelligence/commit/e31cf4fced0bbbf908f06ee5a4d05a1dcba57639))


### Documentation

* add Docker Compose development setup with Vite HMR for Studio ([2b93672](https://github.com/bcit-tlu/course-intelligence/commit/2b936721a11be115d120c6de389e0c6ba41c05ab))

## [0.14.0](https://github.com/bcit-tlu/course-intelligence/compare/backend-v0.13.0...backend-v0.14.0) (2026-08-28)


### Features

* consolidate developer documentation into main docs page ([1e6aad3](https://github.com/bcit-tlu/course-intelligence/commit/1e6aad3bb0772b67c9ac2f17c8c2039d74291422))

## [0.13.0](https://github.com/bcit-tlu/course-intelligence/compare/backend-v0.12.0...backend-v0.13.0) (2026-08-28)


### Features

* add developer documentation with rehype-slug for heading anchors ([9014df9](https://github.com/bcit-tlu/course-intelligence/commit/9014df9135e0ddcdfa26b2c2f017332295ac344c))

## [0.12.0](https://github.com/bcit-tlu/course-intelligence/compare/backend-v0.11.0...backend-v0.12.0) (2026-08-28)


### Features

* add frontend and backend analytics with OpenTelemetry events an… ([82af942](https://github.com/bcit-tlu/course-intelligence/commit/82af9427704ad51d378e9d5714289c81a61fff30))
* add frontend and backend analytics with OpenTelemetry events and metrics ([cb2e48e](https://github.com/bcit-tlu/course-intelligence/commit/cb2e48e5cf2c61637eeabadee14ddc6a8ac80162))
* add OpenTelemetry Web SDK dependencies for frontend instrumentation ([40585ce](https://github.com/bcit-tlu/course-intelligence/commit/40585ce9ebe69a9b3bb591ba9c95c0f811e312dd))


### Bug Fixes

* consolidate OpenTelemetry logs imports into single line ([d95fa9f](https://github.com/bcit-tlu/course-intelligence/commit/d95fa9f33337aea4e1114471ca527f88c4817c49))
* update Resource instantiation to use constructor instead of deprecated create method ([4775978](https://github.com/bcit-tlu/course-intelligence/commit/4775978a7637f8d5285e6f90f666f8423854688c))

## [0.11.0](https://github.com/bcit-tlu/course-intelligence/compare/backend-v0.10.6...backend-v0.11.0) (2026-08-27)


### Features

* add OpenTelemetry instrumentation and Grafana dashboards ([4b84a76](https://github.com/bcit-tlu/course-intelligence/commit/4b84a76cbd5ba7f32795d928a3cc9dda0f8866c3))
* add OpenTelemetry instrumentation and Grafana dashboards ([4ef7dc9](https://github.com/bcit-tlu/course-intelligence/commit/4ef7dc9b4d85e6a60afd1afb80dbec3b13a6db7f))


### Bug Fixes

* escape Prometheus template variables in Grafana dashboard JSON ([66285cf](https://github.com/bcit-tlu/course-intelligence/commit/66285cf3cfa8495a43b779dc519ca51d17a007dd))

## [0.10.6](https://github.com/bcit-tlu/course-intelligence/compare/backend-v0.10.5...backend-v0.10.6) (2026-08-24)


### Documentation

* add LiteLLM provider documentation and clarify retention behavior ([a443d0f](https://github.com/bcit-tlu/course-intelligence/commit/a443d0f7c03a8435eed86604f2f15bc174b98e2c))

## [0.10.5](https://github.com/bcit-tlu/course-intelligence/compare/backend-v0.10.4...backend-v0.10.5) (2026-08-12)


### Documentation

* add MCP server design section to architecture documentation ([58b1655](https://github.com/bcit-tlu/course-intelligence/commit/58b16554c85981e8a39a3cccb8ea189a8afae530))
* add MCP server design section to architecture documentation ([be4f8ae](https://github.com/bcit-tlu/course-intelligence/commit/be4f8aead30a246616f25c425cb3cb604cf3b574))

## [0.10.4](https://github.com/bcit-tlu/course-intelligence/compare/backend-v0.10.3...backend-v0.10.4) (2026-08-12)


### Documentation

* clarify Helm release names vs workload names in deployment guide ([fc4d6a0](https://github.com/bcit-tlu/course-intelligence/commit/fc4d6a05991370dace2d8ff79306ccd805bead4b))

## [0.10.3](https://github.com/bcit-tlu/course-intelligence/compare/backend-v0.10.2...backend-v0.10.3) (2026-08-12)


### Documentation

* update project description from Dialog to Course Intelligence t… ([08ae342](https://github.com/bcit-tlu/course-intelligence/commit/08ae342a914e0dc3beea1063a4fc5a66009747df))
* update project description from Dialog to Course Intelligence throughout documentation ([1da1c0c](https://github.com/bcit-tlu/course-intelligence/commit/1da1c0c07bb840321893eb211b39eec67c9f6a4f))

## [0.10.2](https://github.com/bcit-tlu/course-intelligence/compare/backend-v0.10.1...backend-v0.10.2) (2026-08-12)


### Documentation

* update code references from dialog to course_intelligence in documentation and comments ([23a1ccc](https://github.com/bcit-tlu/course-intelligence/commit/23a1cccaaedfe50c406589e8b4c9c7060ec28c44))

## [0.10.1](https://github.com/bcit-tlu/dialog/compare/backend-v0.10.0...backend-v0.10.1) (2026-08-12)


### Documentation

* update architecture documentation with product component model … ([b370adb](https://github.com/bcit-tlu/dialog/commit/b370adbbae0e693f6598b8f37680ee753e21031c))
* update architecture documentation with product component model and naming conventions ([ca5aa59](https://github.com/bcit-tlu/dialog/commit/ca5aa590c255d6a14f1db5ab94135ebb65614a56))

## [0.10.0](https://github.com/bcit-tlu/dialog/compare/backend-v0.9.1...backend-v0.10.0) (2026-08-10)


### Features

* 82 add user manual documentation page to the react frontend ([70104ed](https://github.com/bcit-tlu/dialog/commit/70104ed8e2a67bc3ace00a659be08ea0f6051fdf))


### Documentation

* add in-app user manual with markdown rendering ([ed4989e](https://github.com/bcit-tlu/dialog/commit/ed4989e0476ebe564272df9267d8422e68e15013))
* update project descriptions to reflect broader course processing scope ([41bfbfc](https://github.com/bcit-tlu/dialog/commit/41bfbfce870706f98ba59a584110a9d616d2525f))

## [0.9.1](https://github.com/bcit-tlu/dialog/compare/backend-v0.9.0...backend-v0.9.1) (2026-08-10)


### Documentation

* remove duplicate changelog entries and expand architecture docu… ([e1a5c04](https://github.com/bcit-tlu/dialog/commit/e1a5c043c37bb51ce4ea658d4a7ec6ed1026b1d5))
* remove duplicate changelog entries and expand architecture documentation ([5d77dc8](https://github.com/bcit-tlu/dialog/commit/5d77dc8a02a953e27f46637f36d5c19c38f13402))

## [0.9.0](https://github.com/bcit-tlu/dialog/compare/backend-v0.8.2...backend-v0.9.0) (2026-08-06)


### Features

* add per-node progress tracking with current_step field ([5f12ea1](https://github.com/bcit-tlu/dialog/commit/5f12ea17f7f3c1584ade23d11049cd73f7fb4c27))
* add per-node progress tracking with current_step field ([2d68c78](https://github.com/bcit-tlu/dialog/commit/2d68c78e1e1c48185d64647ebbd177f0515bdfdb))

## [0.8.2](https://github.com/bcit-tlu/dialog/compare/backend-v0.8.1...backend-v0.8.2) (2026-08-06)


### Documentation

* update deployment guide to reflect Flux GitOps workflow ([336535c](https://github.com/bcit-tlu/dialog/commit/336535c22e4d6a0fbc83df7817b6bfa345578b7c))

## [0.8.1](https://github.com/bcit-tlu/dialog/compare/backend-v0.8.0...backend-v0.8.1) (2026-08-06)


### Bug Fixes

* delete old jobs entirely instead of blanking storage_key ([150437a](https://github.com/bcit-tlu/dialog/commit/150437aa378a89370df419a6a27bc608bb1d675e))

## [0.8.0](https://github.com/bcit-tlu/dialog/compare/backend-v0.7.0...backend-v0.8.0) (2026-08-06)


### Features

* add Helm chart configuration for upload retention count ([c097e21](https://github.com/bcit-tlu/dialog/commit/c097e2133999c5cca1ecdeeb893860e2fd3421e3))

## [0.7.0](https://github.com/bcit-tlu/dialog/compare/backend-v0.6.0...backend-v0.7.0) (2026-08-06)


### Features

* add configurable upload retention with automatic S3 cleanup ([5fb5ea1](https://github.com/bcit-tlu/dialog/commit/5fb5ea1edc037fd50bd97e1937409ffdd7c55053))
* add configurable upload retention with automatic S3 cleanup ([250ff6e](https://github.com/bcit-tlu/dialog/commit/250ff6ec507341e03f46cf4129f13f68d0204eab))

## [0.6.0](https://github.com/bcit-tlu/dialog/compare/backend-v0.5.1...backend-v0.6.0) (2026-08-06)


### Features

* add generic directory parser with natural sorting and nested D2… ([04947c1](https://github.com/bcit-tlu/dialog/commit/04947c11771c8c9dff50793d58be498982f63c4c))
* add generic directory parser with natural sorting and nested D2L ToC support ([5c44e67](https://github.com/bcit-tlu/dialog/commit/5c44e672f650ca13df5facd7388e7bc72677efb2))

## [0.5.1](https://github.com/bcit-tlu/dialog/compare/backend-v0.5.0...backend-v0.5.1) (2026-08-05)


### Bug Fixes

* add LLM_MAX_TOKENS config to prevent truncated JSON responses ([b0e04e6](https://github.com/bcit-tlu/dialog/commit/b0e04e65dd9626ca966f41b376545de7284ccb30))

## [0.5.0](https://github.com/bcit-tlu/dialog/compare/backend-v0.4.0...backend-v0.5.0) (2026-08-05)


### Features

* add OLLAMA_MODEL config and configmap checksum annotations ([4e86a42](https://github.com/bcit-tlu/dialog/commit/4e86a4279226b2fe0e30c2ff15274de77d7f91b1))
* add OLLAMA_MODEL config and configmap checksum annotations to force pod restarts on config changes ([a839669](https://github.com/bcit-tlu/dialog/commit/a839669a7733195756a38d0313e15a720521fb20))
* Merge pull request [#62](https://github.com/bcit-tlu/dialog/issues/62) from bcit-tlu/61-llm-provider-integration-plan ([4e86a42](https://github.com/bcit-tlu/dialog/commit/4e86a4279226b2fe0e30c2ff15274de77d7f91b1))

## [0.4.0](https://github.com/bcit-tlu/dialog/compare/backend-v0.3.0...backend-v0.4.0) (2026-07-31)


### Features

* add 120 second timeout to minio bucket creation job ([bf00b41](https://github.com/bcit-tlu/dialog/commit/bf00b4136ebcf1ca13ccd0bd0a317436864db49c))

## [0.3.0](https://github.com/bcit-tlu/dialog/compare/backend-v0.2.0...backend-v0.3.0) (2026-07-30)


### Features

* add nodeSelector, tolerations, and affinity support for postgres, redis, and minio deployments ([056909d](https://github.com/bcit-tlu/dialog/commit/056909db095d6b85c4cf7ada47ecb1094085f54c))

## [0.2.0](https://github.com/bcit-tlu/dialog/compare/backend-v0.1.3...backend-v0.2.0) (2026-07-30)


### Features

* add job listing endpoint with tenant filtering and history UI ([3178f19](https://github.com/bcit-tlu/dialog/commit/3178f19344a90801b983fec4cb3f9d0714d51e56))
* add job listing endpoint with tenant filtering and history UI ([48d6749](https://github.com/bcit-tlu/dialog/commit/48d6749bcdccb4795f7ea9eb97295fcd33677674))
* Merge pull request [#55](https://github.com/bcit-tlu/dialog/issues/55) from bcit-tlu/54-job-discovery-reconnection ([3178f19](https://github.com/bcit-tlu/dialog/commit/3178f19344a90801b983fec4cb3f9d0714d51e56))

## [0.1.3](https://github.com/bcit-tlu/dialog/compare/backend-v0.1.2...backend-v0.1.3) (2026-07-29)


### Bug Fixes

* opt in to nginx local resolvers entrypoint in frontend chart ([84f3305](https://github.com/bcit-tlu/dialog/commit/84f330559d0be411cb3697e20dabb7700321aa91))

## [0.1.2](https://github.com/bcit-tlu/dialog/compare/backend-v0.1.1...backend-v0.1.2) (2026-07-29)


### Bug Fixes

* Merge pull request [#49](https://github.com/bcit-tlu/dialog/issues/49) from bcit-tlu/48-frontend-nginx-resolver-and-backend-llm-secret-reference ([a09e8de](https://github.com/bcit-tlu/dialog/commit/a09e8deafe2d7594835106c92cce1f0e6a0bc50d))
* replace hardcoded NGINX_DNS_RESOLVER with NGINX_LOCAL_RESOLVERS ([a09e8de](https://github.com/bcit-tlu/dialog/commit/a09e8deafe2d7594835106c92cce1f0e6a0bc50d))

## [0.1.1](https://github.com/bcit-tlu/dialog/compare/backend-v0.1.0...backend-v0.1.1) (2026-07-29)


### Bug Fixes

* **frontend:** use generic examples for learning objectives placeholder ([b5aaa2c](https://github.com/bcit-tlu/dialog/commit/b5aaa2cd6f1c84c1bf3b405c14bd4c74c7f29a61))
* **frontend:** use generic examples for learning objectives placeholder ([b5aaa2c](https://github.com/bcit-tlu/dialog/commit/b5aaa2cd6f1c84c1bf3b405c14bd4c74c7f29a61))
