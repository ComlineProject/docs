# `http`

Types for talking HTTP: request methods, requests and responses.

Plain data types: use them as fields and arguments in your own schemas.

| | |
|---|---|
| enum [`HttpMethod`](#httpmethod) | An HTTP request method. |
| struct [`Request`](#request) | An HTTP request: its method and target URI. |
| struct [`Response`](#response) | An HTTP response, by its status code. |

<a id="httpmethod"></a>

## enum `HttpMethod`

An HTTP request method.

Variants:

- `GET`
- `POST`
- `PUT`
- `DELETE`

<a id="request"></a>

## struct `Request`

An HTTP request: its method and target URI.

| Field | Type | |
|---|---|---|
| `method` | [`HttpMethod`](#httpmethod) |  |
| `uri` | `string` |  |

<a id="response"></a>

## struct `Response`

An HTTP response, by its status code.

| Field | Type | |
|---|---|---|
| `status_code` | `u16` |  |
