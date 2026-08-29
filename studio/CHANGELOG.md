# Changelog

## [0.10.0](https://github.com/bcit-tlu/course-intelligence/compare/studio-v0.9.0...studio-v0.10.0) (2026-08-29)


### Features

* add sub-step progress tracking with live UI updates ([62b6606](https://github.com/bcit-tlu/course-intelligence/commit/62b6606dc674b697886f894751deffb5ec8fa471))
* integrate sub-step progress into overall progress calculation ([ac3783f](https://github.com/bcit-tlu/course-intelligence/commit/ac3783f1ef7b5f8685da1b3a9ec76045cf753bd7))


### Bug Fixes

* 139 real time progress updates ([8fd66b5](https://github.com/bcit-tlu/course-intelligence/commit/8fd66b5fa16319a51f0cc10901d1f958267da7fc))

## [0.9.0](https://github.com/bcit-tlu/course-intelligence/compare/studio-v0.8.0...studio-v0.9.0) (2026-08-29)


### Features

* add job duration display with live elapsed time for processing jobs ([03f106c](https://github.com/bcit-tlu/course-intelligence/commit/03f106c0818e8be789097d0bcc2f21066265d7ca))


### Bug Fixes

* 136 job timeout watchdog ([7e06451](https://github.com/bcit-tlu/course-intelligence/commit/7e0645180256638917bd83b33ec495c2c7212b99))

## [0.8.0](https://github.com/bcit-tlu/course-intelligence/compare/studio-v0.7.0...studio-v0.8.0) (2026-08-28)


### Features

* display total log count in LevelFilter "All" badge ([a90c5a5](https://github.com/bcit-tlu/course-intelligence/commit/a90c5a5dfedc708eb7651ae2efc86587ab03e93e))


### Bug Fixes

* configure Vite dev server for Docker with dynamic backend URL and disable OTel in dev ([7fef26c](https://github.com/bcit-tlu/course-intelligence/commit/7fef26c10c72a8657b4e319951b12a287a5941d9))
* remove .env.local generation from dev container and auto-detect Docker environment ([e31cf4f](https://github.com/bcit-tlu/course-intelligence/commit/e31cf4fced0bbbf908f06ee5a4d05a1dcba57639))

## [0.7.0](https://github.com/bcit-tlu/course-intelligence/compare/studio-v0.6.0...studio-v0.7.0) (2026-08-28)


### Features

* consolidate developer documentation into main docs page ([1e6aad3](https://github.com/bcit-tlu/course-intelligence/commit/1e6aad3bb0772b67c9ac2f17c8c2039d74291422))

## [0.6.0](https://github.com/bcit-tlu/course-intelligence/compare/studio-v0.5.0...studio-v0.6.0) (2026-08-28)


### Features

* add developer documentation with rehype-slug for heading anchors ([9014df9](https://github.com/bcit-tlu/course-intelligence/commit/9014df9135e0ddcdfa26b2c2f017332295ac344c))

## [0.5.0](https://github.com/bcit-tlu/course-intelligence/compare/studio-v0.4.0...studio-v0.5.0) (2026-08-28)


### Features

* add frontend and backend analytics with OpenTelemetry events an… ([82af942](https://github.com/bcit-tlu/course-intelligence/commit/82af9427704ad51d378e9d5714289c81a61fff30))
* add frontend and backend analytics with OpenTelemetry events and metrics ([cb2e48e](https://github.com/bcit-tlu/course-intelligence/commit/cb2e48e5cf2c61637eeabadee14ddc6a8ac80162))
* add OpenTelemetry Web SDK dependencies for frontend instrumentation ([40585ce](https://github.com/bcit-tlu/course-intelligence/commit/40585ce9ebe69a9b3bb591ba9c95c0f811e312dd))


### Bug Fixes

* update Resource instantiation to use constructor instead of deprecated create method ([4775978](https://github.com/bcit-tlu/course-intelligence/commit/4775978a7637f8d5285e6f90f666f8423854688c))

## [0.4.0](https://github.com/bcit-tlu/dialog/compare/frontend-v0.3.0...frontend-v0.4.0) (2026-08-10)


### Features

* 82 add user manual documentation page to the react frontend ([70104ed](https://github.com/bcit-tlu/dialog/commit/70104ed8e2a67bc3ace00a659be08ea0f6051fdf))

## [0.4.0](https://github.com/bcit-tlu/dialog/compare/frontend-v0.3.0...frontend-v0.4.0) (2026-08-10)


### Features

* 82 add user manual documentation page to the react frontend ([70104ed](https://github.com/bcit-tlu/dialog/commit/70104ed8e2a67bc3ace00a659be08ea0f6051fdf))

## [0.3.0](https://github.com/bcit-tlu/dialog/compare/frontend-v0.2.0...frontend-v0.3.0) (2026-08-06)


### Features

* add per-node progress tracking with current_step field ([5f12ea1](https://github.com/bcit-tlu/dialog/commit/5f12ea17f7f3c1584ade23d11049cd73f7fb4c27))
* add per-node progress tracking with current_step field ([2d68c78](https://github.com/bcit-tlu/dialog/commit/2d68c78e1e1c48185d64647ebbd177f0515bdfdb))

## [0.2.0](https://github.com/bcit-tlu/dialog/compare/frontend-v0.1.2...frontend-v0.2.0) (2026-07-30)


### Features

* add job listing endpoint with tenant filtering and history UI ([3178f19](https://github.com/bcit-tlu/dialog/commit/3178f19344a90801b983fec4cb3f9d0714d51e56))
* add job listing endpoint with tenant filtering and history UI ([48d6749](https://github.com/bcit-tlu/dialog/commit/48d6749bcdccb4795f7ea9eb97295fcd33677674))
* Merge pull request [#55](https://github.com/bcit-tlu/dialog/issues/55) from bcit-tlu/54-job-discovery-reconnection ([3178f19](https://github.com/bcit-tlu/dialog/commit/3178f19344a90801b983fec4cb3f9d0714d51e56))

## [0.1.2](https://github.com/bcit-tlu/dialog/compare/frontend-v0.1.1...frontend-v0.1.2) (2026-07-29)


### Bug Fixes

* Merge pull request [#49](https://github.com/bcit-tlu/dialog/issues/49) from bcit-tlu/48-frontend-nginx-resolver-and-backend-llm-secret-reference ([a09e8de](https://github.com/bcit-tlu/dialog/commit/a09e8deafe2d7594835106c92cce1f0e6a0bc50d))
* replace hardcoded NGINX_DNS_RESOLVER with NGINX_LOCAL_RESOLVERS ([a09e8de](https://github.com/bcit-tlu/dialog/commit/a09e8deafe2d7594835106c92cce1f0e6a0bc50d))

## [0.1.1](https://github.com/bcit-tlu/dialog/compare/frontend-v0.1.0...frontend-v0.1.1) (2026-07-29)


### Bug Fixes

* **frontend:** use generic examples for learning objectives placeholder ([b5aaa2c](https://github.com/bcit-tlu/dialog/commit/b5aaa2cd6f1c84c1bf3b405c14bd4c74c7f29a61))
* **frontend:** use generic examples for learning objectives placeholder ([b5aaa2c](https://github.com/bcit-tlu/dialog/commit/b5aaa2cd6f1c84c1bf3b405c14bd4c74c7f29a61))

## [0.1.1](https://github.com/bcit-tlu/dialog/compare/frontend-v0.1.0...frontend-v0.1.1) (2026-07-29)


### Bug Fixes

* **frontend:** use generic examples for learning objectives placeholder ([b5aaa2c](https://github.com/bcit-tlu/dialog/commit/b5aaa2cd6f1c84c1bf3b405c14bd4c74c7f29a61))
* **frontend:** use generic examples for learning objectives placeholder ([b5aaa2c](https://github.com/bcit-tlu/dialog/commit/b5aaa2cd6f1c84c1bf3b405c14bd4c74c7f29a61))
