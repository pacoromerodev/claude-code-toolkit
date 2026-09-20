#!/usr/bin/env bash
# A migration dropping a column that the checked-in code still reads.
set -euo pipefail

mkdir -p src/main/resources/db/migration src/main/java/app

cat > src/main/resources/db/migration/V7__drop_legacy_reference.sql <<'SQL'
ALTER TABLE orders DROP COLUMN legacy_reference;
CREATE INDEX idx_orders_status ON orders (status);
SQL

cat > src/main/java/app/OrderRepository.java <<'JAVA'
package app;

import java.util.List;

public interface OrderRepository {

    // Still reading the column the migration drops.
    @Query("SELECT o.legacyReference FROM Order o WHERE o.id = :id")
    String findLegacyReference(Long id);

    List<Order> findByStatus(String status);
}
JAVA

git init -q -b main .
git config user.email eval@example.invalid
git config user.name "Eval Fixture"
git add -A
git commit -qm "Add order repository"
