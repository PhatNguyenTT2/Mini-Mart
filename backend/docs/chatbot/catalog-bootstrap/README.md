# Catalog bootstrap tools

These scripts are separate catalog/customer bootstrap utilities. They are not
executed during an R3 or production training campaign.

`seed-5000.sql` is the current 5,200-SKU catalog seed used by benchmark v5. Its
bytes are treated as an immutable, hash-bound catalog input; this does not make
the bootstrap command itself part of the benchmark runtime. The historical
1,380-SKU service seed is not the current benchmark catalog.

Behavior generation remains defined under `seed-product/`. The v5.1 amendment
uses the same 5,200 raw SKU identifiers and derives a controlled family-level
content view without rerunning this bootstrap or mutating a database.
