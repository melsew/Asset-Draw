# Asset-Draw standalone verifiers (protocol asset-draw/v1)

Two independent implementations, neither importing backend code:

    python verifier/verify_draw.py package.json
    node verifier/js/cli.mjs package.json

`verifier/js/verify.mjs` also runs in browsers and is what the public verification page embeds.
Both must agree with every vector in `tests/vectors/draw_v1.json` (enforced by backend tests).
