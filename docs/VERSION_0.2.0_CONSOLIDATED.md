# TUNEL-CORE 0.2.0 — Versão Consolidada

Data de consolidação: 11/08/2026.

## Estado

- Produto TUNEL-CORE: finalizado no escopo da Fase 2.
- Código-fonte: completo para o contrato arquitetural aprovado.
- Persistência, durabilidade, recuperação seletiva, multicanais bilaterais, controle de fluxo e bootstrap: implementados.
- Supervisor e Watchdog: independentes e com recuperação seletiva.
- Inicialização no Windows: projetada para serviço automático antes do login.
- CI: matriz Windows/Linux aprovada antes da consolidação.
- Integração com sistemas externos: etapa independente e não altera a conclusão do produto Core.

## Fronteira soberana

```text
Sistema externo
    |
    v
Adapter específico
    |
    v
TUNEL-CORE
    |
    v
Runtime fornecido pelo sistema integrador
```

O TUNEL-CORE não incorpora lógica específica de aplicação nem possui runtime concreto obrigatório.

Para Windows MCP, `tunnel-client` pertence ao Windows MCP. A ponte entre ambos é um Adapter específico. Essa dependência não é incorporada ao núcleo universal.

## Contrato de arquitetura

```text
APLICAÇÃO != CORE != SUPERVISOR != WATCHDOG != RUNTIME
```

O Core mantém separação entre Control Plane e Data Plane, usa ownership/lease/fencing para evitar disputa, não autoriza encerramento por PID isolado, usa filas limitadas e backpressure, e mantém capacidade multicanal configurável.

## Capacidade baseline

- operação normal: 16 canais;
- pico inicial: 32 canais;
- limite arquitetural: configurável conforme recursos e runtime integrador.

## Marco

Versão: `0.2.0`
Estado: `CONSOLIDATED`
Fase: `PHASE_2_CORE_COMPLETE`
TUNEL_CORE_MISSION_PROVEN: `TRUE`
