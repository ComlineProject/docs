"""Pygments lexers for Comline's own languages: the `.ids` schema language
and the `.idp` package-manifest language.

Grammars are kept in sync by hand against the real grammars in
`comline-core` (`src/schema/idl/grammar.rs`, `src/package/config/idl/grammar.rs`)
— not re-derived from the parser, so a grammar change can silently drift
this. Good enough for documentation highlighting; not a validator.
"""
