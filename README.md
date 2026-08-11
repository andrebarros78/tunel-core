# TUNEL-CORE

Núcleo universal de conectividade persistente, multicanal, bilateral e autorrecuperável.

## Versão consolidada

**TUNEL-CORE 0.2.0 — PHASE_2_CORE_COMPLETE — CONSOLIDATED**

O TUNEL-CORE é um produto independente. Integrações com aplicações, provedores ou runtimes concretos pertencem aos sistemas integradores e são realizadas exclusivamente por Adapter.

No caso do Windows MCP, `tunnel-client` pertence ao Windows MCP e não ao TUNEL-CORE.

Documento de consolidação: `docs/VERSION_0.2.0_CONSOLIDATED.md`.

## Arquitetura

O Core mantém conexões e canais disponíveis com baixa interferência no caminho de dados, persistência resistente a crash, recuperação seletiva e isolamento entre aplicação, runtime, Supervisor e Watchdog.

```text
Aplicação externa
      │
      ▼
Adapter
      │
      ▼
TUNEL-CORE
 ├─ Control Plane
 │   ├─ Connection / Profiles / Credentials
 │   ├─ Health / Recovery / Reliability
 │   ├─ Ownership / Lease / Fencing
 │   ├─ Persistence / Checkpoint / Rollback
 │   └─ Supervisor
 │
 └─ Data Plane
     ├─ Transport / Provider adapters
     ├─ Multi-Channel Manager
     ├─ Backpressure / priority lanes
     └─ High-flow streaming
      │
      ▼
Runtime externo do sistema integrador
```

Regra estrutural: **APLICAÇÃO ≠ CORE ≠ SUPERVISOR ≠ WATCHDOG ≠ RUNTIME**.

## Propriedades

- 16 canais simultâneos como baseline normal e 32 como pico inicial; capacidade arquitetural configurável.
- canais independentes e bilaterais;
- sem lock global no caminho de dados;
- filas limitadas e backpressure obrigatório;
- hot replacement de canal degradado;
- health com histerese;
- retry com orçamento, backoff e jitter;
- circuit breaker por domínio de falha;
- ownership por lease/fencing para evitar split-brain;
- identidade de processo não depende apenas de PID;
- persistência com gravação atômica e journal;
- checkpoint e rollback;
- Supervisor corrige apenas recurso degradado sob sua responsabilidade;
- Watchdog observa apenas o Supervisor;
- bootstrap recupera estado antes da convergência;
- atualização transacional com health gate;
- segredos são referências e nunca estado persistido do Core.

## Boot Windows

`installers/windows/install.ps1` cria um ambiente Python privado em `%ProgramData%\TUNEL-CORE`, instala o pacote localmente e registra `TUNELCOREWatchdog` como serviço `Automatic`. O serviço inicia sem login de usuário e recompõe o Supervisor. Se ainda não houver Adapter de runtime configurado, o Supervisor permanece saudável aguardando integração externa.

## Layout principal

```text
src/tunel_core/
  control_plane.py
  data_plane.py
  ownership.py
  persistence_engine.py
  reliability.py
  observability.py
  bootstrap.py
  plugins.py
  runner.py
  selftest.py
  supervisor.py
  watchdog.py
```

## Validação

O CI executa em Windows e Linux, compila todos os módulos, executa pytest e verifica que caminhos/projetos específicos não retornaram ao Core.

A integração com runtime/provedor concreto é uma fase independente de implantação.
