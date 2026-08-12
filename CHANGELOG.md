# Changelog

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
