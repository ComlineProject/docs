# std

The Comline standard library.

Built into the toolchain: every package can `use std::…` with no entry in
`config.idp`, and a build includes only the std schemas a package imports.
Its version is the toolchain's.

## Modules

| Module | |
|---|---|
| [`http`](http.md) | Types for talking HTTP: request methods, requests and responses. |
| [`validators`](validators.md) | Validators to attach to fields with `@validators`. |
