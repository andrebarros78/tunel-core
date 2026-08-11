# TUNEL-CORE

Núcleo universal de conectividade persistente, multicanal, bilateral e autorrecuperável.

## Objetivo V0.2 / Fase 2

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
Runtime externo
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

`installers/windows/install.ps1` cria um ambiente Python privado em `%ProgramData%\TUNEL-CORE`, instala o pacote localmente e registra `TUNELCOREWatchdog` como serviço `Automatic`. O serviço inicia sem login de usuário e recompõe o Supervisor. Se ainda não houver Adapter de runtime configurado, o Supervisor permanece saudável em `waiting_runtime_adapter` até a integração externa ser fornecida.

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

A integração com um runtime/provedor concreto é feita exclusivamente por Adapter e pertence à fase de implantação no ambiente operacional.
