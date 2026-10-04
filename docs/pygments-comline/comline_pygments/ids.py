"""Lexer for Comline's `.ids` schema language.

Token set follows `core/src/schema/idl/grammar.rs` (mirrored by
`core/src/schema/idl/vocabulary.rs` for Rust-side consumers like the
language server — this lexer can't depend on that crate directly, so it
stays a manual mirror): keywords, the twelve primitive types, `///`
docstrings vs. `//` comments, `@key=value` annotations, and the three
literal forms (`"..."` strings, `f"..."` f-strings, bare integers).
`True`/`False` are capitalised here — that's the real grammar, not a typo
(contrast `.idp`'s lowercase `true`/`false`).
"""

from pygments.lexer import RegexLexer, bygroups, words
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

__all__ = ["IdsLexer"]

_KEYWORDS = (
    "import", "use", "self", "parent", "package", "as", "const", "type",
    "optional", "struct", "error", "enum", "settings", "validator",
    "validate", "assert", "and", "or", "protocol", "function", "union",
)

_PRIMITIVES = (
    "s8", "s16", "s32", "s64", "u8", "u16", "u32", "u64", "f32", "f64",
    "bool", "str", "string",
)

# Keywords that are immediately followed by the name they declare — matched
# as one rule each so the name gets its own token instead of falling through
# to the generic identifier rule.
_DECL_KEYWORDS = ("struct", "enum", "protocol", "error", "validator")


class IdsLexer(RegexLexer):
    """Lexer for Comline schema files (`.ids`)."""

    name = "Comline IDL"
    aliases = ["ids", "comline-ids"]
    filenames = ["*.ids"]

    tokens = {
        "root": [
            (r"\s+", Whitespace),
            (r"///[^\n]*", Comment.Special),
            (r"//[^\n]*", Comment.Single),
            (r"@[a-zA-Z_][a-zA-Z0-9_]*", Name.Decorator),
            (r"\b(True|False)\b", Keyword.Constant),
            (
                r"\b(%s)(\s+)([a-zA-Z_][a-zA-Z0-9_]*)" % "|".join(_DECL_KEYWORDS),
                bygroups(Keyword, Whitespace, Name.Class),
            ),
            (
                r"\b(function)(\s+)([a-zA-Z_][a-zA-Z0-9_]*)",
                bygroups(Keyword, Whitespace, Name.Function),
            ),
            (
                r"\b(type)(\s+)([a-zA-Z_][a-zA-Z0-9_]*)",
                bygroups(Keyword, Whitespace, Name.Class),
            ),
            (
                r"\b(const)(\s+)([a-zA-Z_][a-zA-Z0-9_]*)",
                bygroups(Keyword, Whitespace, Name.Constant),
            ),
            # `message` is a keyword only in `error { message = "..." }` —
            # everywhere else (e.g. a field named `message`) it's a plain
            # name, so it's matched here instead of in `_KEYWORDS`.
            (r"\b(message)(\s*)(=)", bygroups(Keyword, Whitespace, Operator)),
            (words(_KEYWORDS, prefix=r"\b", suffix=r"\b"), Keyword),
            (words(_PRIMITIVES, prefix=r"\b", suffix=r"\b"), Keyword.Type),
            (r'f"[^"]*"', String.Interpol),
            (r'"[^"]*"', String.Double),
            (r"-?\d+", Number.Integer),
            (r"->|::|==|!=|>=|<=", Operator),
            (r"[!@=:;,.*<>]", Operator),
            (r"[{}()\[\]]", Punctuation),
            (r"[a-zA-Z_][a-zA-Z0-9_]*", Name),
        ],
    }
