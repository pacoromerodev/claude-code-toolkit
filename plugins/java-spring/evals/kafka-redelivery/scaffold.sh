#!/usr/bin/env bash
set -euo pipefail
mkdir -p src/main/java/app src/main/resources

cat > src/main/java/app/PaymentListener.java <<'JAVA'
package app;

import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Component
public class PaymentListener {

    private final PaymentGateway gateway;
    private final LedgerRepository ledger;

    public PaymentListener(PaymentGateway gateway, LedgerRepository ledger) {
        this.gateway = gateway;
        this.ledger = ledger;
    }

    @KafkaListener(topics = "payments", groupId = "payment-processor")
    public void onPayment(PaymentRequested event) {
        gateway.charge(event.customerId(), event.amount());
        ledger.increment(event.customerId(), event.amount());
    }
}
JAVA

cat > src/main/resources/application.yml <<'YAML'
spring:
  kafka:
    bootstrap-servers: localhost:9092
    consumer:
      enable-auto-commit: true
      auto-commit-interval: 5000
      auto-offset-reset: latest
YAML
