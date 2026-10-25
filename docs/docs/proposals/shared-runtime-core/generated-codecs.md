# Codecs and protocol glue generated from one plan

Status: **under discussion** · part of [Shared runtime core](index.md) · stage 3

**The question:** codecs are the largest per-language cost, and they work on
each host's own typed values, so they can't sit behind the
[core boundary](core-interface.md) without converting every value on every
call. How do ten or more languages get codecs that are as fast as the host
allows and provably identical to each other, without ten hand-written codecs
per wire format?

The answer proposed here: the shared codegen kernel computes **one wire layout
plan** per type and format, and each language's generator renders it into
**native, specialized encode and decode functions** over a small set of
primitives. The per-protocol glue every generator re-derives today is planned
the same way. Every option is held to the [constraint](index.md#the-constraint):
correctness, conformance and performance together, with nothing traded away.

## Where things stand

No generator emits per-type encode or decode code today. Three different
mechanisms do the byte work:

| Where | What does the bytes | Lines on `main` |
|---|---|---|
| Rust runtime, `runtime/core/src/format/packed.rs` | a serde `Serializer` and `Deserializer` for `packed@1`, `no_std`, no `alloc` | 1,015 (737 code, 278 tests) |
| Rust runtime, `format/json.rs`, `format/msgpack.rs` | thin wrappers over `serde_json` and `rmp-serde`, both `std`-gated | 56, 89 |
| TypeScript runtime, `runtime/src/packed.ts` | `PackedCodec`, a generic codec that walks a `Layout` at run time | 534 |
| TypeScript runtime, `runtime/src/json.ts`, `codec.ts` | an exact JSON parser to a `JsonNode` tree, then a walk driven by a `Shape` | 272, 36 |
| Simulator, `src/packed.rs` | the Rust runtime's `Packed`, driven from a run-time `TypeDef` over `serde_json::Value` | 791 (~520 code, the rest tests) |

### Rust

- **`packed@1` is a serde data format.** Its rules are in the module doc:
  - fixed-width little-endian numbers, and `bool` as `00` or `01`;
  - strings and bytes as a varint length, then the bytes;
  - sequences as a varint count; tuples and fixed arrays with no count;
  - an option as `00`, or `01` and the value;
  - struct fields in declaration order, with no names;
  - an enum as its variant index as a varint.
- **Decoding is strict.** A varint must be in its shortest form, at most 10
  bytes, with the tenth byte holding bit 63 alone. A length larger than the
  bytes left is refused before anything is allocated. Bad `bool` and option
  tags and invalid UTF-8 are refused, and so is a value that doesn't use every
  byte (`decode_seed`).
- **Unknown enum variants are refused by serde's derive,** not by the format:
  `Packed` hands the index to the derived visitor, which rejects one out of
  range.
- **The generator emits serde derives** (`comline-rust/codegen/src/generator.rs`):
  `#[derive(Serialize, Deserialize)]` on structs, errors, C-like enums and
  params structs, with `serde_rename` for wire names, `#[serde(borrow)]` on
  borrowed params, and `serde_big_array` for fixed arrays longer than 32.
  Unions are refused before rendering, by the kernel's
  `features::refuse_unsupported` and Rust's `SUPPORT` table.

### TypeScript

- **The generator emits a `Layout` constant beside each type**
  (`<Name>Layout`, from `fields_layout` and `TypeMapper::layout` in
  `comline-typescript/codegen/src/generator.rs`). A named type is referenced
  lazily, `() => MessageLayout`, so types can refer to each other in any order.
- **`PackedCodec` walks that `Layout` for every value.** For each node it:
  - resolves thunks in a loop (`resolve`);
  - switches on a string tag or probes `"array" in l`, `"struct" in l` and so on;
  - looks integer widths up in a table;
  - for a union, scans members with `holds()` to find the first that can hold
    the value by its JavaScript kind;
  - reads every varint, including every string length, as a `bigint`;
  - builds each decoded struct with `Object.fromEntries` and a `filter`.
- **JSON goes through two passes.** `parseJson` builds a `JsonNode` tree with a
  `Map` per object, then `decodeJson` walks it against a `Shape`. `JsonCodec`
  rebuilds that `Shape` from the `Layout` with `jsonShape()` on every decode.
  The exact parser exists because `JSON.parse` rounds integers above 2^53.
- **JSON encoding doesn't see the schema.** `stringifyJson` writes the object's
  own keys. A field the object lacks is left out where Rust writes `null`, and
  a property the schema doesn't declare goes onto the wire.
- **JSON decoding doesn't check widths or variants:** comline-typescript#57 is
  open. There is no MessagePack codec at all (`codec.ts`: "a later addition").

### The simulator

- **It has no generated types.** Values are JSON, so `src/packed.rs` wraps them
  in a `Typed` `Serialize` and a `Seed` `DeserializeSeed` that follow the
  project's `TypeDef`s, and hands both to the runtime's own `Packed`.
- **Its bytes are the reference's by construction,** because it calls the
  reference serializer. It's an interpreter of the schema, which suits a
  simulator and is not what an application should run.

### The shared kernel and its precedent

- **`comline-codegen`** (`generation/codegen/src`) is 3,737 lines in 12 files on
  `master`. The accepted [resolution kernel](../codegen-architecture/resolution-kernel.md)
  put symbols, modules, naming and collisions there.
- **`validation.rs` (467 lines) is the "plan once, render per language"
  precedent.** It follows alias chains across schemas, binds every validator
  property to a value, and returns a language-neutral
  `Plan { base, checks, elements, nested }`. `comline-rust/codegen/src/validate.rs`
  (383 lines) lowers it into an `impl Validate` per type and the shadow type
  `validate_on_decode` needs. TypeScript hasn't lowered it yet.
- **`connections.rs` (443 lines) already centralizes part of the glue:**
  framing resolution (`framing`, protocol `@framing` over the package's
  `wire.framing` over `datagram@2`), `on_connection`, JSON-RPC method names,
  protocol numbers and the connection IR hash.

### The glue each generator still re-derives

Each generator's `protocol()` rebuilds the same per-protocol decisions from
frozen IR:

| | Rust | TypeScript |
|---|---|---|
| File | `generator.rs`, 2,184 lines (tests from line 2,075) | `generator.rs`, 1,635 lines |
| Protocol glue | `protocol()` from line 1,097, plus `async_dispatcher`, `async_sender`, `dispatch_arms` and `fn_info`: about 800 lines | `protocol()`, lines 1,032 to about 1,395 |
| Its own `FnInfo` | yes | yes |
| `UnknownError{o}` fallback for an ordinal with no error type | in `fn_info` | inline in `protocol()` |
| Undecodable params: one-way drops, request/response faults | `dispatch_arms` | the `try`/`catch` in the dispatcher |
| Client outcome: ok, fault, err by ordinal, `Remote{id}` | `Envelope` match | `"ok" in env`, `"fault" in env`, `switch (env.err.id)` |
| JSON-RPC carries JSON whatever the package format is | `format_of` | `default_codec` |
| Framing name to runtime type | `framing_for` | `framing_for` |

The copies already differ: Rust's dispatcher runs param checks when
`validate_on_decode` asks for it, and TypeScript's has no such step.

## The proposal

### 1. A wire layout plan in the kernel

A new `comline-codegen` module, `layout.rs`, computes a **`LayoutPlan`** for a
generation request and a wire format. The plan is a small tree per named
type, with every decision a codec needs already made:

- **field order:** declaration order, with wire names;
- **fixed widths and endianness:** each scalar's width, little-endian;
- **varint lengths and enum indexes:** where a varint goes, and which ones are
  counts that must not exceed the bytes left;
- **option presence:** a presence byte in `packed@1`, `null`-or-missing in
  JSON, `nil` in MessagePack;
- **union tags:** the member index;
- **fixed arrays vs sequences:** `T[N]` has no count, `T[]` has one;
- **aliases resolved:** a `type` alias is its target on the wire, followed
  across schemas the way `validation.rs` follows it;
- **strictness for decode:** refuse overlong or oversized varints, `bool` and
  presence bytes other than `00` and `01`, union tags and enum indexes out of
  range, unknown variants, integers out of range for their type, invalid
  UTF-8, lengths past the end, and trailing bytes.

A sketch:

```rust
// generation/codegen/src/layout.rs

/// The wire formats a plan can be computed for.
pub enum Format { Packed1, Json1, MsgPack1 }

/// Every type a request's bodies reach, for one format.
pub struct LayoutPlan {
    pub format: Format,
    pub rules: Rules,
    /// One entry per named type, alias chains already followed, so an
    /// alias never appears here.
    pub types: Vec<TypePlan>,
    /// Each function's params, return value and error bodies, by `TypeId`.
    pub bodies: Vec<BodyPlan>,
}

pub struct TypePlan {
    pub id: TypeId,
    /// Namespace and declared name, from the symbol table.
    pub origin: Origin,
    pub node: Node,
    /// Bytes every value of this type takes, when that is fixed
    /// (no strings, sequences, options or unions anywhere below).
    pub fixed_size: Option<u32>,
}

pub enum Node {
    Unit,
    Scalar(Scalar),
    Str,
    /// A varint count, then the elements. `u8` elements are one copy.
    Seq(Box<Node>),
    /// Exactly `len` elements, no count.
    Fixed { element: Box<Node>, len: u32 },
    /// Presence, then the value.
    Option(Box<Node>),
    Struct { fields: Vec<Field> },
    /// Variants in declaration order, with their wire names.
    Enum { variants: Vec<String> },
    /// The member index, then the member.
    Union { members: Vec<Node> },
    /// A named struct, error or enum: a call to its own function, which is
    /// what lets types be recursive.
    Ref(TypeId),
}

pub enum Scalar { Bool, U8, U16, U32, U64, U128, S8, S16, S32, S64, S128, F32, F64 }

pub struct Field { pub wire_name: String, pub node: Node }

/// What the format decides, as the conformance profile records it.
pub struct Rules {
    pub fields: ByPosition | ByName,
    pub variants: ByIndex | ByName,
    pub integers: FixedLe | JsonDigits | MsgPackByValue,
    pub absent: PresenceByte | WriteNullAcceptMissing | Nil,
    pub unknown_field: Reject | Skip,
    pub trailing_bytes: Reject,
    pub varints: ShortestLeb128Max10,
}
```

(`Rules` is written loosely; each field would be its own small enum.)

- **A tree, not a flat op list.** A tree keeps recursion (`Ref`) and nesting
  explicit, which every renderer needs to produce one function per named type.
  The renderer walks it once at generate time, so the tree costs nothing at
  run time. A backend that wants a flat op list, a C backend say, can flatten
  it locally.
- **`Rules` are the conformance profile's facts.** `profiles/packed@1.json`,
  `json@1.json` and `msgpack@1.json` already record `struct_fields`,
  `unknown_field`, `missing_optional`, `enum_variants`, `unknown_variant` and
  `integer_width`, each proven by named vectors. A kernel test checks that
  `Rules` for each format agrees with its profile, so the plan can't drift from
  what the corpus proves.
- **`fixed_size` lets a renderer check bounds once** for a run of fixed-width
  fields, instead of once per field.

### 2. Each language renders native code from the plan

A backend turns each `TypePlan` into an encode and a decode function in its
own language: straight-line code specialized to that type, with no reflection,
no schema walk and no `Layout` object at run time.

For `struct Player { id: u64, name: str, class: Class, pos: f32[3], guild?: u32 }`
under `packed@1`, the TypeScript backend would render something like:

```ts
export function encodePlayer(w: Writer, v: Player): void {
  w.u64(v.id);
  w.str(v.name);
  w.varint(encodeClass(v.class));
  const pos = v.pos;
  if (pos.length !== 3) refuse();
  w.f32(pos[0]!); w.f32(pos[1]!); w.f32(pos[2]!);
  if (v.guild === undefined) w.u8(0);
  else { w.u8(1); w.u32(v.guild); }
}

export function decodePlayer(r: Reader): Player {
  const id = r.u64();
  const name = r.str();
  const class_ = decodeClass(r.index(CLASS_VARIANTS));
  r.need(12);
  const pos: [number, number, number] = [r.f32Unchecked(), r.f32Unchecked(), r.f32Unchecked()];
  const guild = r.presence() ? r.u32() : undefined;
  return guild === undefined ? { id, name, class: class_, pos } : { id, name, class: class_, pos, guild };
}
```

- **Host-width checks are rendered too.** Where the host type is wider than
  the wire type (a JavaScript `number` for a `u8`, a Python `int` for a `u32`),
  the encoder refuses a value out of range, as `PackedCodec` does today. The
  plan gives the wire type; the backend knows its own host type.
- **Unions still need a host rule.** The plan fixes the wire tag. How a host
  value picks its member is the backend's mapping, and it must be unambiguous
  (see [Open questions](#open-questions)).
- **Validation can join decode.** The same backend that lowers
  `validation::Plan` can run a field's checks right after decoding it, which is
  what `validate_on_decode` asks for.

### 3. A small primitive set per language

Each language's runtime keeps only the primitives the rendered code calls.
For the binary formats (`packed@1`, and the integer and length encodings
MessagePack needs) the set is:

| Writer | Reader |
|---|---|
| `u8`, `u16`, `u32`, `u64`, `u128`, little-endian; signed as two's complement | `u8` … `u128`, little-endian, each bounds-checked |
| `f32`, `f64`, the bits as given, no NaN canonicalization | `f32`, `f64`, the bits as given |
| `varint(u64)`, shortest LEB128 | `varint()`: at most 10 bytes, tenth byte ≤ `01`, no trailing `00` byte |
| `bytes(raw)`, no length | `len()`: a varint no larger than the bytes left |
| `str(s)`: varint byte length, then UTF-8 | `str()`: `len()`, then strict UTF-8 |
| `reserve(n)`, for a fixed-size run | `need(n)` and unchecked reads after it, for a fixed-size run |
| | `bool()` and `presence()`: `00` or `01`, else refuse |
| | `index(n)`: a varint below `n`, else refuse |
| | `finish()`: refuse unless every byte was used |

- **One error kind,** as Rust's `RuntimeError::Serialization`, with a reason
  kept for tests.
- **About 150 lines in most languages.** TypeScript's `Writer` and `Reader`
  classes in `packed.ts` are this set already, at about 200 lines with
  comments. What goes is the `Layout` walk around them.
- **The set is where hosts differ,** so it's where stage 1's
  [differential fuzzing](verification.md) aims hardest: varint edge cases,
  128-bit values, NaN bit patterns, invalid UTF-8.

### 4. JSON and MessagePack

**JSON is self-describing,** and each host has its own parsers. The plan still
decides everything that isn't syntax:

- **Field names** are the plan's wire names. A rendered encoder writes each
  `"name":` prefix as a constant. A rendered decoder matches keys with a
  generated `switch`, which is what makes `unknown_field: ignored` cheap.
- **64-bit and 128-bit integers.** `json@1` writes them as bare numbers with
  all their digits: the vectors `format-json/u64-above-2-53` and `u64-max`
  pin it. Writing them as strings would be a different wire format, a
  `json@2`, not something a backend may choose. A decoder must parse the digits
  exactly into the field's width and refuse a value out of range
  (`decode-wider-integer-overflow`). That's why `json.ts` exists:
  `JSON.parse` rounds above 2^53.
- **Absent optionals.** `json@1` writes `null` (`struct-optional-none`) and
  accepts either `null` or a missing member (`missing_optional: absent`).
  Optional-field omission was one of the five TypeScript interop bugs, and
  `stringifyJson` still omits a member the host object lacks. A rendered
  encoder writes exactly the plan's fields, so the bytes no longer depend on
  how the host object was built.
- **Equality is RFC 8259 equality.** Vectors compare JSON by value
  (`"compare": "json"`), numbers exactly, member order ignored. That stays the
  rule for vectors and for fuzzing; `jsonEqual` in `json.ts` is TypeScript's
  copy of it.
- **The JSON primitive set** must guarantee:
  - string escaping and unescaping per RFC 8259, with lone surrogates refused;
  - exact integer parsing into a given width, with a range check;
  - float writing that reads back to the same bits, and correctly rounded
    float parsing;
  - skipping one well-formed value, for an ignored member;
  - refusing trailing text after the value;
  - one pull tokenizer, so a rendered decoder reads straight into the host
    type with no intermediate tree.
- **A host's own JSON parser may be used** only where it meets that list, and
  where stage 1's fuzzing proves it equal to the reference. Python's `json`
  keeps integers exact; JavaScript's `JSON.parse` does not, so TypeScript keeps
  an exact tokenizer. Which is faster on a given host is for the benchmark
  gates to say.

**MessagePack is the same shape with different rules.** Per its profile and
`rmp-serde`'s behaviour, structs are positional arrays, enum variants go by
name, and integers are read by value, not by declared width. TypeScript has no
MessagePack codec today, so rendering one from the plan is how it gets one.

### 5. Rust: keep serde, and prove the plan against it

Two choices for the Rust backend:

| | Keep serde derives | Render Rust from the plan |
|---|---|---|
| Privileged path | yes: Rust's bytes don't come from the plan | no: Rust is one more consumer |
| Independent oracle for the plan | **yes:** serde and the plan are two separate derivations of the rules | **no:** a plan bug would appear identically in Rust and every other language, and differential fuzzing against Rust could no longer see it |
| Speed | already fast; monomorphized and `no_std` | possibly faster in places (bulk `u8` copies, one bounds check per fixed run, no `&mut dyn BufMut` call per byte); unmeasured |
| Zero-copy decode | `&'a str` borrowed from the input today | would have to be rendered again |
| Other users | `Packed::decode_seed` drives the simulator | none |

**Recommendation: keep serde derives as Rust's production path, and as the
reference.** The deciding reason is the constraint itself. The whole stage 1
design rests on fuzzing every language against an independent reference. If
Rust also rendered from the plan, the plan would have no independent check,
and a mistake in it would be "conformant" everywhere at once.

The plan still gets proven in Rust first:

- **A CI-only Rust renderer.** The kernel's tests render the plan to Rust and
  run [differential fuzzing](verification.md) between the plan-rendered code
  and serde with `Packed`, `Json` and `MsgPack`, over the conformance types
  and generated random ones. Random values must encode to identical bytes, and
  the same malformed inputs must be refused by both.
- **This proves the plan before any other language renders it,** in the
  language where both sides are cheapest to run. A failure there is a plan bug,
  not a backend bug.
- **Switching Rust's production path is a measurement, not a preference.** If
  the gates show plan-rendered Rust clearly faster than serde, it can become
  the production path, and serde stays as the test oracle. Until then nothing
  changes for Rust users.

### 6. Why this is the fast option

- **Specialized code beats a generic walker.** Rendered code does none of the
  work `PackedCodec` does per value: no thunk resolution, no string switches
  or `in` probes, no table lookups, no `holds()` scans, no `bigint` varints for
  lengths that fit a `number`, no `Object.fromEntries`. The JSON path loses the
  `JsonNode` tree and the per-decode `jsonShape()`.
- **Native code beats a boundary crossing.** A codec in the core would first
  convert the host object into something the core can read, which is a full
  walk of the value plus a copy, and then encode it: strictly more work than one
  native walk that writes bytes. See
  [Alternatives rejected](#alternatives-rejected).
- **No number is claimed here.** There is no benchmark anywhere in the org
  today. The [benchmark gates](verification.md) must prove, per language and
  format, over a corpus of type shapes (flat scalars, strings, deep nesting,
  large `u8` sequences, unions):
  - rendered code is at least as fast as the codec it replaces
    (`PackedCodec`, `JsonCodec`) before that codec is deleted;
  - each language meets its performance budget afterwards;
  - generated code size, for browser bundles, where a generic walker is
    smaller. Rendering one function per named type, and loops instead of
    unrolling past a small fixed length, keeps that bounded.

## Protocol glue, planned once

The per-protocol decisions in the [glue table](#the-glue-each-generator-still-re-derives)
are facts about the schema, not about a language. Following the accepted
[resolution kernel](../codegen-architecture/resolution-kernel.md) direction,
and next to `connections.rs`, which already holds part of it, the kernel
computes a **`ProtocolPlan`** that backends render:

```rust
// generation/codegen/src/protocol.rs

pub struct ProtocolPlan {
    pub origin: Origin,
    pub provider: Provider,               // from connections.rs
    pub framing: FramingValue,            // resolved by connections::framing
    pub on_connection: bool,
    pub number: Option<u16>,              // connections::protocol_number
    pub handshake: Handshake,             // comline@1 or none, and @unverified
    /// JSON-RPC carries JSON whatever the package's format is.
    pub body_format: BodyFormat,          // Package | Json
    /// The call table, in schema order: index = datagram call id.
    pub calls: Vec<CallPlan>,
    /// Every `!` across the protocol, by ordinal, deduplicated.
    pub errors: Vec<ErrorRef>,
}

pub struct CallPlan {
    pub index: u16,
    pub name: String,
    pub method: String,                   // bare or qualified, from connections.rs
    pub params: Option<BodyId>,           // into the LayoutPlan
    pub ret: Return,                      // OneWay | Unit | Value(BodyId)
    pub errors: Vec<ErrorRef>,            // empty for a one-way call
    pub timeout_ms: Option<u64>,
    pub validate_params: bool,
}

pub enum ErrorRef {
    Known { ordinal: u16, body: BodyId },
    /// No error type found for the ordinal: today's `UnknownError{o}`.
    Unknown { ordinal: u16 },
}
```

The policies become rules in one place instead of code in each generator:

- **Server side.**
  - Params that don't decode, or fail their checks: a one-way call stops with
    no reply; a request/response call answers with a fault.
  - The handler returns a value: reply `ok` with it encoded.
  - It returns a declared error: reply `err` with that ordinal and the error
    encoded.
  - Anything else: a fault. A one-way call never replies.
- **Client side.** `ok` decodes the return value; `fault` is a provider fault;
  `err` with a declared ordinal decodes that error; any other ordinal is
  `Remote { id }`.
- **Body format.** JSON for a JSON-RPC protocol, the package's format
  otherwise.

A backend renders those rules in its own idiom: `Result` and `Fault<E>` in
Rust, `throw` and error classes in TypeScript, exceptions or result types
elsewhere. The plan says what happens, and the backend decides only how it's
spelled. That retires both `FnInfo`s, both `UnknownError{o}` fallbacks, and
the `format_of` / `default_codec` and `framing_for` pairs, and closes the
`validate_params` gap between the two dispatchers.

## What a new language then costs

| | Today | With stages 2 and 3 |
|---|---|---|
| Runtime | about 2,350 lines in TypeScript: codecs, framings, handshake, connection, envelopes | the primitive set (about 150 lines binary, plus a JSON set) and a thin binding to the core ([core interface](core-interface.md)) |
| Generator | 1,635 lines in TypeScript, about 2,075 non-test in Rust | type mapping, naming, manifests, plus a renderer for `LayoutPlan` and `ProtocolPlan` |
| Proof | the vendored vectors | vectors, differential fuzzing and benchmark gates ([verification](verification.md)) |

The renderer's size is unknown until a second backend renders the plan; it
should be measured on TypeScript in the rollout below, not estimated here. What
is certain is what it no longer contains: no format rules, no strictness rules,
no fault policy and no error mapping, which are the parts that drifted.

## Alternatives rejected

- **A schema-driven codec in the core.** Every call would convert host values
  into a form the core reads, then encode: two walks and a copy where native
  code does one walk. That fails performance in every language. It also needs
  the schema at run time in every process. The simulator does exactly this,
  correctly, because it has no generated types. It's a fine tool there and the
  wrong main path.
- **A generic codec per language walking a schema at run time.** This is
  TypeScript today. It's correct where it's been tested, but it is slower than
  specialized code by construction: it decides at run time, for every value,
  what the generator already knew. It also still needs a hand-written codec per
  format per language. It fails performance, and it doesn't solve the cost.
- **Hand-written codecs per language,** the status quo. Ten languages times
  three formats is thirty codecs whose agreement rests on vectors someone wrote
  down. Five interop bugs on the corpus's first day, and #57 still open, show
  what that costs in correctness and conformance.

## Open questions

- **Unions on the host.** The plan fixes the wire tag. TypeScript picks the
  first member that can hold a value by its JavaScript kind, so in `u8 | u16`
  the value `5` always goes to `u8`. Rust refuses unions; the simulator takes
  the index. Should the kernel refuse unions whose members a host can't tell
  apart, or should generated hosts carry an explicit tag?
- **Duplicate JSON keys.** serde's derive refuses a repeated field;
  TypeScript's `parseJson` keeps the last one. No vector covers it.
- **Non-finite floats in JSON.** JSON has no NaN or infinity. What `json@1`
  does with one should be written down and vectored, not left to each host's
  writer.
- **Third-party encodings.** Can an encoding defined the
  [extensibility](../extensibility.md) way declare its rules for the plan,
  instead of shipping a codec per language? `Rules` would then have to be data,
  not a closed set of enums.
- **The plan's form.** It's an in-process Rust value while generators are Rust
  crates. If generators ever run out of process
  ([Proposal D](../codegen-architecture/target-language-plugins.md)), the plan
  needs a stable serialized form.
- **Validation inside decode.** Should `LayoutPlan` and `validation::Plan` merge,
  so a rendered decoder checks a field as it reads it?
- **Code size budgets** for browser targets, and where the gates set them.

## Rollout

Every step is gated by [stage 1](verification.md). Nothing is deleted until the
gates show its replacement is equal and at least as fast.

1. **The plan in the kernel.** `layout.rs` with `LayoutPlan` and `Rules`, a test
   that `Rules` matches each conformance profile, and the CI-only Rust renderer
   fuzzed against serde.
2. **`packed@1` first.** It's the default format, it has the strictest rules,
   and TypeScript's `PackedCodec` is the clearest generic walker to beat.
   - The TypeScript backend renders encode and decode functions per type.
   - `PackedCodec` and the `Layout` constants stay until the gates pass, then go.
3. **JSON, then MessagePack.**
   - TypeScript's JSON codec moves to rendered code with an exact tokenizer.
   - `parseJson` stays for the JSON-RPC framing until stage 4 moves framing to
     the core, and `jsonEqual` stays as the test comparator.
   - TypeScript gains MessagePack.
4. **The glue.** `protocol.rs` with `ProtocolPlan`; both generators render it,
   and the duplicated `FnInfo`, fallbacks and policies go.

## What it touches

- **generation** (`comline-codegen`): new `layout.rs` and `protocol.rs`, built
  on `symbols.rs` and `connections.rs`; profile-agreement tests; the CI-only
  Rust renderer.
- **comline-rust:** keeps serde derives; renders `ProtocolPlan` in place of its
  own `FnInfo`, `dispatch_arms` policy and client mapping.
- **comline-typescript:** a plan renderer in the generator. The runtime keeps
  `Writer`, `Reader` and a JSON tokenizer, and loses `PackedCodec`, `JsonCodec`'s
  `Shape` walk, `jsonShape` and the generated `Layout` constants once the gates
  pass.
- **runtime:** the conformance profiles become an input the kernel is tested
  against. `format::Packed`, `Json` and `MsgPack` stay as the reference.
- **simulator:** unchanged. It keeps driving the reference serializer from its
  schema.
- **Docs:** the TypeScript and Rust language guides' format sections, and
  [How generators are built](../codegen-architecture/index.md).
