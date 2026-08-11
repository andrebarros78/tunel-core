# TUNEL-CORE

Núcleo universal de conexão persistente, supervisão, recuperação e estado.

## Fronteira arquitetural

```text
Controlador externo
   ↓
TUNEL-CORE
   ↓
Supervisor / Watchdog
   ↓
Adapter de túnel
   ↓
Aplicação local observada
```

Regra estrutural: **APLICAÇÃO ≠ TÚNEL ≠ SUPERVISOR ≠ WATCHDOG**.

O Core não contém API externa, credenciais reais, regras de aplicação, vínculos a projetos locais, letras de unidade, tarefas agendadas específicas ou caminhos absolutos de uma instalação anterior.

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
2. Identidade exige, quando disponível, executable path, command line, parent PID e fingerprint.
3. Falha do túnel não autoriza reinício de aplicação saudável.
4. Watchdog recupera somente o Supervisor.
5. Recovery é seletivo e usa retry/backoff.
6. Credenciais são referências; segredos não entram em perfis nem no código.
7. Nenhum lock global para todas as conexões.
8. Caminhos de runtime são resolvidos por configuração ou diretórios do próprio produto.
9. Nenhuma aplicação específica pode ser incorporada ao núcleo.

## Estado

V1 universalizada. Integrações concretas entram exclusivamente por Adapter e configuração externa.
