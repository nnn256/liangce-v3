# TDX bridge

Implements the supplied `oficcejo/tdx-api` `/api/kline-all/tdx` and `/api/batch-quote` contracts using its pinned Go protocol implementation. It binds to loopback and is called only by the research backend. The upstream standalone service can also be configured through `LIANGCE_TDX_API`.

Source reference: https://github.com/oficcejo/tdx-api/tree/ea07dccb67aeb92ebde851ac31503b4bf457a318 . Original protocol project: https://github.com/injoyai/tdx . The Python alternative is https://github.com/acb6104/opentdx/tree/f2bcc1501c10be1771d3b17483770ee3fcc91933 . The alternative uses Python3.12+, yuan prices and share volumes; the REST protocol uses integer milli-yuan prices and lot volumes. Never combine units implicitly.

The Docker build downloads source at the pinned commit and builds our small bridge entry point. No upstream database, executable or private data is included. Full pages mean all rows the provider returns; minute retention is finite and year bars may be insufficient for structure.
