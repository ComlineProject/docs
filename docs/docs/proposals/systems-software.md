# Comline for systems software

Status: **draft** · Scope decided 2026-11-02 (below) · Builds on
[IPC](ipc.md), [Transports](transports.md) and
[bounds on types](type-bounds/index.md)

**The question:** can Comline describe the interfaces of drivers and other
systems software, and what would it need to?

"Writing drivers with Comline" covers four uses, with very different costs:

| Use | Examples | What Comline needs | Fit today |
|---|---|---|---|
| **1. User-space drivers and their clients** | Fuchsia drivers, Android hardware layers, macOS DriverKit, Windows UMDF, Linux VFIO and libusb services | [IPC](ipc.md), with handles | close |
| **2. Kernel ↔ user-space interfaces** | ioctl structures, netlink messages, io_uring-style shared rings | an exact memory layout, fixed sizes, no allocation | partial |
| **3. Hardware protocols** | register maps, USB descriptors, HID reports, I2C and SPI commands, CAN frames, Bluetooth GATT | bit fields, byte order per field, fixed offsets | far |
| **4. Generated code inside a kernel** | Rust for Linux, Windows kernel drivers in C | target constraints and a C generator | far |

**Decided 2026-11-02:** 1 first, through [IPC](ipc.md); 2 planned, with an
exact-layout format and target constraints; 3 and 4 later.

Where things stand:

- **The Rust runtime's lowest tier** is `no_std` with no allocator: framing,
  dispatch and decoding over buffers the caller provides
  ([runtime contract](../design/core-target-contract.md)). `packed@1` needs no
  allocator.
- **Decoders are hardened:** a hostile length is refused before allocating,
  buffers are zeroed after each call, and generated code forbids `unsafe`.
- **Generated code isn't `no_std` yet**
  ([comline-rust#83](https://github.com/ComlineProject/comline-rust/issues/83)).
- **The C ABI** exposes the shared runtime core, but no generator writes C
  types.
- **With every value bounded** ([issue 6](type-bounds/max-only.md#issues-and-resolutions)),
  every message has a known worst-case size: a target without an allocator can
  hold each message in a buffer sized at build time.

## An exact-layout format

For shared memory, ioctl structures and reading values in place, both sides
need the same bytes at the same offsets. No current format gives that:

| | `packed@1` | An exact-layout format |
|---|---|---|
| Layout | fields one after another, no padding | fixed offsets, with alignment and padding as the target's C ABI lays them out |
| Lengths | varint prefixes | none: everything fixed-size |
| Reading | front to back | any field, in place, at its offset |
| Byte order | little-endian | the target's own, or stated |

What it would define:

- **Only fixed-size types:** scalars, `T[N]`, structs of them. A bounded array
  `T[max N]` takes room for N items plus a count. Unbounded types can't appear,
  which [issue 6](type-bounds/max-only.md#issues-and-resolutions) already
  ensures.
- **Strings:** a `char[max N]` keeps its meaning (characters) and takes a
  length plus 4 × N bytes of UTF-8 room: correct, if wasteful, for interfaces
  designed in Comline. C's own text is a type of its own,
  [`c_char`](#c-text-stdffic_char).
- **`optional`, enums and unions:** a presence flag, and a tag of a stated
  width.
- **The same layout in every language:** generated Rust uses `#[repr(C)]`,
  generated C a plain struct, and each states its size and offsets as
  compile-time checks, so a mismatch fails the build, not the kernel.
- **Any layout change is breaking:** offsets move.

How it's named and versioned (a format such as `c-layout@1`, parameterized by
target ABI) is open.

### C text: `std::ffi::c_char`

Proposed 2026-11-02. C structures measure text in **bytes**, end it with a NUL,
and often promise no encoding (Linux file names are arbitrary bytes). Comline's
`char[max N]` counts **characters** and is always valid Unicode. Rather than
bend one onto the other, C text gets its own element type, the way `char` is
Unicode text's:

```ids
use std::ffi::c_char

struct InterfaceRequest {
    /// C's `char ifr_name[16]`: up to 15 bytes of text, then a NUL.
    name: c_char[16]
    flags: u16
}
```

- **`c_char[N]` is C's `char name[N]`, one to one:** N bytes of storage holding
  up to N − 1 bytes of text, then a NUL. A C header translates directly.
- **Why an element type, not `CString[16]`:** a suffix after a name means an
  array of it ([issue 2](type-bounds/max-only.md#issues-and-resolutions)), so
  a sized type has to be an array of an element, as `char[N]` is.
- **In std, as `std::ffi::c_char`,** not a global keyword, following Rust's
  `core::ffi::c_char`. It's the first std type whose meaning core knows, so
  generators treat it specially, as they already build in std's validators.
- **Checked:** decoding refuses an array without a NUL; encoding refuses text of
  N bytes or more; converting a `char[]` refuses U+0000, which C would read as
  the end of the text.
- **Encoding is a validator:** `Utf8()` when an interface promises UTF-8,
  nothing for raw bytes.
- **Generated code:** C, `char name[16]`, byte-identical to existing headers;
  Rust, a 16-byte array type with `as_bytes()` and a fallible `to_str()`;
  TypeScript, bytes with a decode helper.
- **Open:** NUL-padded fields that may fill all N bytes without a NUL, as some
  fixed formats use (a second type, or a variant); how `json@1` shows
  `c_char[N]`.

## Target constraints

A target states what its generated code may and may not do, and the build
checks the schema against it:

| Constraint | Values | What the build does |
|---|---|---|
| Allocation | none, fallible only, or global | **none:** every message gets a fixed buffer sized from its worst case. **Fallible:** allocations that can fail return an error, never panic (as Rust for Linux requires) |
| Floating point | allowed or not | not allowed (most kernel contexts): `f32` and `f64` are refused for that target |
| Panics | allowed or not | not allowed: generated code is total, failing with errors only |
| Stack | a budget in bytes | decoding recursion (`@max_depth`) times its frame size is checked against it |
| `unsafe` | forbidden or allowed | forbidden by default, as today |

- **Declared by the target,** with defaults per kind of target (a kernel, an
  embedded device), and narrowed by the consumer's configuration.
- **Proven, not trusted:** CI builds the generated code under the constraints
  (`#![no_std]`, no `alloc`, `panic = "abort"`), and checks it can't panic.
- **Hover shows** which targets a schema can't be generated for, and why.

## A C generator

Kernel interfaces (2) and kernel code (4) are mostly C. The C ABI already
carries the runtime; a generator for C types and their (de)coders would carry
the schema. It's needed for 4, and useful for 2.

## Hardware protocols, later

Bit fields, byte order per field and fixed offsets are a different kind of
format from what Comline has. When 3 is taken up, it likely starts from
[packet dispatch](packet-dispatch.md)'s legacy framings.

## Prior art

| System | What to learn |
|---|---|
| Linux UAPI headers | the C structures user space and the kernel share |
| Linux netlink specifications (YAML, `tools/net/ynl`) | a kernel interface described in a spec, with code generated from it |
| Fuchsia FIDL drivers | drivers whose interfaces are an IDL over IPC |
| Android HIDL and AIDL hardware layers | driver interfaces as versioned IDL |
| macOS DriverKit (IIG) | user-space drivers with interfaces generated from a description |
| Rust for Linux | fallible allocation, no panics, no floating point |

## Phasing

1. **[IPC](ipc.md):** transports, handles, peer identity, peer death. Use 1.
2. **Target constraints,** with `no_std` generated code
   (comline-rust#83) as the first target.
3. **The exact-layout format.** Use 2.
4. **A C generator.**
5. **Later:** hardware protocols (3) and kernel code (4).

## Open

- **The exact-layout format:** its name, and how a target ABI is named.
- **C text:** `std::ffi::c_char` as [proposed](#c-text-stdffic_char), NUL-padded
  fields, and `json@1`.
- **Target constraints:** the list, their defaults per kind of target, and
  where they're declared.
- **Proving no panics:** which checks CI runs.
- **The C generator:** its place in the plan, and whether it renders from the
  [codec plan](shared-runtime-core/generated-codecs.md) like the others.
