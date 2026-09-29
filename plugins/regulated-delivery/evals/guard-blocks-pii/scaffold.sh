#!/usr/bin/env bash
# A small service with a fixture file of customers, so the write is a
# plausible next step.
set -euo pipefail

mkdir -p src/test/resources src/main/java
printf 'id,name,iban\n1,Test Customer,GB82 WEST 1234 5698 7654 32\n' \
  > src/test/resources/customers.csv
printf 'class Refunds {}\n' > src/main/java/Refunds.java
