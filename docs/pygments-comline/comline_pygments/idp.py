"""Lexer for Comline's `.idp` package-manifest language (`config.idp`).

Token set follows `core/src/package/config/idl/grammar.rs`: the single
`congregation NAME` header, flat `key = value` assignments, and the three
special key forms the grammar itself distinguishes — a namespaced key
(`a::b::c`), a version-tagged one (`rust#1.70.0`), and a dependency
address (`name@version::path`). Booleans are lowercase `true`/`false`
here — contrast `.ids`'s capitalised `True`/`False`, which is the real
grammar, not a mismatch to fix.
"""

from pygments.lexer import RegexLexer, bygroups
from pygments.token import (
    Comment,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Whitespace,
)

__all__ = ["IdpLexer"]


class IdpLexer(RegexLexer):
    """Lexer for Comline package manifests (`config.idp`)."""

    name = "Comline Config"
    aliases = ["idp", "comline-idp"]
    filenames = ["*.idp", "config.idp"]

    tokens = {
        "root": [
            (r"\s+", Whitespace),
            (r"/\*([^*]|\*[^/])*\*/", Comment.Multiline),
            (r"//.*", Comment.Single),
            (
                r"\b(congregation)(\s+)([a-zA-Z_][a-zA-Z0-9_]*)",
                bygroups(Keyword, Whitespace, Name.Namespace),
            ),
            (r"\b(true|false)\b", Keyword.Constant),
            (r'"(?:[^"\\]|\\["\\/bfnrt]|\\u[0-9a-fA-F]{4})*"', String.Double),
            (r"[a-zA-Z0-9_]+(::[a-zA-Z0-9_]+)*#[a-zA-Z0-9_.]+", Name.Label),
            (
                r"[a-zA-Z0-9_]+(::[a-zA-Z0-9_]+)*@[a-zA-Z0-9_.]+(::[a-zA-Z0-9_.]+)*",
                Name.Label,
            ),
            (r"[a-zA-Z0-9_]+(::[a-zA-Z0-9_]+)+", Name.Namespace),
            (r"[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)+", Name.Variable),
            (r"\d+", Number.Integer),
            (r"[a-zA-Z_][a-zA-Z0-9_]*", Name),
            (r"=", Operator),
            (r"[{}\[\],]", Punctuation),
        ],
    }
