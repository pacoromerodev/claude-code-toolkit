#!/usr/bin/env bash
set -euo pipefail
mkdir -p src/payment src/billing tests

cat > src/payment/PaymentService.java <<'JAVA'
package payment;

public class PaymentService {
    public void charge(String customerId, long amount) {
        // 200 lines of mixed validation, HTTP and persistence, abbreviated.
        if (customerId == null) throw new IllegalArgumentException();
        gateway().post(customerId, amount);
        db().insert(customerId, amount);
    }
}
JAVA

cat > src/billing/InvoiceJob.java <<'JAVA'
package billing;

// Depends on PaymentService.charge; changing its signature breaks this.
public class InvoiceJob {
    void run(PaymentService payments) {
        payments.charge("c-1", 100L);
    }
}
JAVA

echo "placeholder" > tests/PaymentServiceTest.java
git init -q -b main . && git config user.email eval@example.invalid && \
  git config user.name "Eval Fixture" && git add -A && git commit -qm "Initial"
