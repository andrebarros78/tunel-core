# TUNEL-CORE

Núcleo universal de conexão persistente, recuperação e supervisão.

## Fronteira arquitetural

```text
Pipo / IA
   ↓
Gateway (API e autenticação — fora deste repositório)
   ↓
TUNEL-CORE
   ↓
Supervisor / Watchdog
   ↓
Túnel
   ↓
Aplicação local (ex.: Windows MCP)
```

Regra estrutural: **APLICAÇÃO ≠ TÚNEL ≠ SUPERVISOR ≠ WATCHDOG**.

O Core não contém API externa, credenciais reais, regras do Windows MCP, vínculos a projetos locais ou caminhos fixos como `C:\Projetos`/`D:\Projetos`.

## Componentes V1

- Connection Manager
- Tunnel Runtime Adapter
- Transport Adapter
- Profile Manager
- Credential Resolver
- Supervisor
- Watchdog
- Health Engine
- Recovery Engine
- Process Identity / Fingerprint
- Single Instance
- State Store
- Persistence / Boot Recovery
- Session / Concurrency primitives
- Observability
- Bootstrap / Self-Test
- Plugin / Adapter interfaces

## Regras de segurança operacional

1. Nunca encerrar processo apenas por PID.
2. Identidade exige, quando disponível: executable path, command line, parent PID e fingerprint.
3. Falha do túnel não autoriza reinício de aplicação saudável.
4. Watchdog recupera Supervisor; não administra diretamente a aplicação.
5. Recovery é seletivo e usa retry/backoff.
6. Credenciais são referências; segredos não entram em perfis nem no código.
7. Nenhum lock global para todas as conexões.

## Estado

Extração V1 iniciada a partir da arquitetura e memória operacional consolidadas do Windows MCP. A integração com o runtime real do `tunnel-client` permanece por Adapter e será validada separadamente no ambiente operacional.
