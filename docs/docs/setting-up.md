# Setting Up Locally

To install and build Comline binaries you might need to install [rust](https://rust-lang.org/)
and [git](https://git-scm.com/)

## Installing CLI

`comline` cli isn't released on crates.io or as an OS package yet, so install it
from source, in which then you can do:

```sh
cargo install --git="https://github.com/ComlineProject/cli" comline
```

This puts the `comline` binary in `~/.cargo/bin`. Check if it's on your `PATH`:

```sh
comline --help
```


!!! info "Distributions"
    `cargo install comline` and OS packages (Fedora, Arch, Windows, macOS) are
    planned; packaging is tracked in
    [`ComlineProject/distributions`](https://github.com/ComlineProject/distributions).


## Installing Language Server

```sh
cargo install --git="https://github.com/ComlineProject/language-server"
```


### Installing Editor Extensions

Its recommended to install the language server

#### VSCode / VSCodium

If you use one of these editors and want to have a better experience, you can install
these extensions from these places (recommendations are ordered):

- [Github Releases](https://github.com/ComlineProject/comline-vscode/tags)

- [Open VSX](-) - **not available yet**

- [VS Marketplace](-) - **not available yet**

!!! info "About Language Server (LSP) and CLI"
    Any platform extension (regardeless of platform) include a bundlender
    language server and CLI bundled, so you might not need to install the language server,
    unless you need diferent versions.

### Vim / Neovim

There is no instructions yet for these

