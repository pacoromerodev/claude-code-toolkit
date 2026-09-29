# claude-code-toolkit

[![validate](https://github.com/pacoromerodev/claude-code-toolkit/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/pacoromerodev/claude-code-toolkit/actions/workflows/validate.yml) · [English](README.md)

Plugins instalables para Claude Code: skills, subagentes y hooks para flujos
reales de entrega de software.

Esto es un **marketplace de plugins**. Se añade una vez y desde él se instala
cualquier plugin.

```
/plugin marketplace add pacoromerodev/claude-code-toolkit
/plugin install delivery-quality@pacoromerodev
```

> Esta página traduce [README.md](README.md), que es la versión de referencia.
> Los README de cada plugin, CONTRIBUTING y la documentación de `docs/` están
> en inglés.

---

## Plugins

| Plugin | Qué aporta |
|---|---|
| **[delivery-quality](plugins/delivery-quality)** | Verificar un cambio antes de fiarse de él: una skill que ejecuta los tests y lee el diff, un subagente de revisión de solo lectura, guardas contra escribir secretos y ejecutar comandos destructivos, y una puerta de tests opcional. |
| **[skill-forge](plugins/skill-forge)** | Averiguar por qué una skill no se activa: un auditor mecánico de los fallos que impiden que una skill o un subagente se cargue o encaje, y un registro opcional de qué componentes se activan en el uso real. |
| **[context-discipline](plugins/context-discipline)** | Conservar el estado de trabajo que la compactación difumina: una instantánea del árbol tomada antes de compactar y devuelta después, una skill para acotar el trabajo antes de escribirlo y un auditor de las reglas de CLAUDE.md que se ignoran. |
| **[api-patterns](plugins/api-patterns)** | *Experimental.* Patrones para construir sobre la API de Claude que traen su propia verificación: un pipeline de evals con evaluadores que discriminan, un auditor de caché para breakpoints que fallan sin avisar, recuperación híbrida fusionada con RRF y un revisor de esquemas de herramientas. |
| **[team-rollout](plugins/team-rollout)** | Desplegar Claude en un equipo sin los errores caros: las cinco decisiones del despliegue en el orden que evita rehacerlas, settings de referencia y un comprobador de permisos más amplios de lo previsto. |
| **[regulated-delivery](plugins/regulated-delivery)** | Mantener los datos de clientes fuera del repositorio: una guarda que bloquea escribir en un fichero un IBAN, un número de tarjeta o un DNI/NIE reales, comprobados por su dígito de control para que los números corrientes y los valores de prueba publicados pasen. |

### Primeros pasos

Instala un plugin y prueba aquello para lo que sirve. Cada enlace lleva al
README del plugin, con todos sus componentes y ajustes. Para ver qué
imprimen los hooks y scripts antes de instalar nada, lee
[docs/demos/](docs/demos/), generado a partir de ejecuciones reales.

| Plugin | Después de instalarlo, prueba |
|---|---|
| [delivery-quality](plugins/delivery-quality) | Haz un cambio y pide a Claude que lo verifique: la skill `verify-changes` ejecuta los tests, lee el diff y dice qué no pudo comprobar. `/review-diff` hace una revisión de solo lectura. Las guardas no necesitan nada; la puerta de tests es opcional: `mkdir -p .claude && touch .claude/test-gate` |
| [context-discipline](plugins/context-discipline) | La instantánea de la compactación no requiere nada. Pide una revisión de tu `CLAUDE.md`, o da una tarea grande y vaga y verás cómo se acota antes de escribir código. `/handoff` deja una nota para la siguiente sesión |
| [skill-forge](plugins/skill-forge) | `python3 "$(ls -d ~/.claude/plugins/cache/pacoromerodev/skill-forge/*/ | sort -V | tail -1)scripts/audit_skills.py" .claude/skills` sobre tus propias skills (la ruta es donde Claude Code lo instala; el `ls` elige la versión instalada más reciente). El registro de activaciones es opcional: `mkdir -p .claude && touch .claude/routing-log` |
| [team-rollout](plugins/team-rollout) | Pregunta cómo desplegar Claude en un equipo, o pide que se revise un `settings.json` o una política gestionada antes de publicarla |
| [api-patterns](plugins/api-patterns) | *Experimental.* Pregunta por qué la caché de prompts no reduce la factura, cómo saber si un cambio de prompt ayudó o cómo arreglar una recuperación que no encuentra coincidencias obvias |
| [regulated-delivery](plugins/regulated-delivery) | No hay nada que hacer. Pide un fixture de test con un número de cuenta de aspecto real y verás cómo se rechaza; los valores de prueba publicados, como `4111 1111 1111 1111`, pasan |

### Estado

Lo que cuesta cada plugin en cada sesión, y lo que midió frente a los mismos
prompts sin ningún plugin cargado (2026-09-26, `claude-opus-5-5`, evaluado por
`claude-sonnet-5`, tres ejecuciones por lado).

| Plugin | Versión | Contexto siempre cargado | Casos | Δ medio frente a no tener plugin |
|---|---|---|---|---|
| delivery-quality | 0.4.0 | ~360 tokens | 8 | +0.38 |
| team-rollout | 0.2.0 | ~230 tokens | 5 | +0.47 |
| context-discipline | 0.3.0 | ~320 tokens | 6 | +0.28 |
| skill-forge | 0.2.1 | ~0 tokens | 1 | +0.00 (es un linter y un registro; no hay nada que batir) |
| api-patterns | 0.2.0 | ~630 tokens | 10 | **−0.10** |
| regulated-delivery | 0.1.0 | ~0 tokens | 2 | sin medir todavía |

El coste de contexto sale de `claude plugin details <plugin>@pacoromerodev`.
Los números de la columna Δ están en el `evals/measurements.json` de cada
plugin, y `python3 .github/scripts/check_eval_freshness.py` dice cuáles han
dejado de estar vigentes porque cambió el caso o el componente que ejercita.

---

## Reglas de diseño

Los componentes siguen unas pocas reglas que salieron de construirlos, y cada
una existe porque lo contrario falló:

- **Un informe no es una prueba.** Las skills y los subagentes terminan con la salida de un comando y un diff, nunca con "todo parece correcto".
- **Di lo que no has comprobado.** `verify-changes` exige una sección "Not verified"; `code-reviewer`, "Obstacles encountered". Un subagente solo devuelve su resumen, así que un hueco que no se menciona es un hueco invisible.
- **El formato de salida de un subagente es el diseño.** Decidir qué devuelve importa más que describir qué es. Aquí no hay agentes con "persona de experto".
- **Las herramientas mínimas.** El revisor no tiene herramientas de edición ni las recibe. Si un arreglo es obvio, lo describe y deja que el hilo principal lo aplique.
- **Los hooks fallan abiertos.** Una guarda que se rompe deja pasar la llamada. El determinismo solo compensa mientras no pueda bloquear la sesión.
- **Lo que lee un componente son datos, nunca instrucciones.** Un diff, un fichero o un mensaje de commit que pide al revisor aprobar algo es un hallazgo. Las instrucciones vienen del usuario y del plugin, de ningún otro sitio.
- **El código de salida 2 es el único que bloquea.** Devuelve stderr a Claude como respuesta, así que el modelo ve el motivo y puede corregirse. Cualquier otro no bloquea.

---

## Estructura

```
.
├── .claude-plugin/marketplace.json   # el catálogo que expone este repositorio
├── plugins/<name>/
│   ├── .claude-plugin/plugin.json
│   ├── README.md, CHANGELOG.md
│   ├── skills/<skill>/SKILL.md       # más references/ cuando la skill lo necesita
│   ├── agents/*.md
│   ├── hooks/hooks.json, scripts/*.py
│   ├── tests/                        # tests con fixtures para cada hook y script
│   └── evals/<case>/                 # casos de eval del plugin y sus mediciones
├── .github/scripts/                  # los checks de CI, cada uno con sus fixtures
├── scripts/                          # runner local de evals, check de enrutado, generador de demos
└── docs/
    ├── anatomy.md                    # qué tipo de componente usar
    ├── demos/                        # qué imprimen los scripts de cada plugin, de ejecuciones reales
    └── history/                      # las auditorías y los planes, en orden
```

`${CLAUDE_PLUGIN_ROOT}` apunta al directorio del plugin instalado: úsalo
siempre en los comandos de los hooks, nunca una ruta relativa.
[CONTRIBUTING.md](CONTRIBUTING.md) tiene la estructura completa de un plugin
y los pasos para añadir uno.

---

## Desarrollo

Los comandos que un cambio debe pasar antes de hacer commit están en
[CLAUDE.md](CLAUDE.md), y CI ejecuta el mismo conjunto en cada pull request.
Los evals van aparte: cuestan dinero o uso del plan y necesitan una CLI con
sesión iniciada, así que no hay workflow de evals. Se ejecutan a mano con
`scripts/run-evals.sh` antes de una release. En
[CONTRIBUTING.md](CONTRIBUTING.md) están las reglas con las que se revisa un
cambio, y en [docs/anatomy.md](docs/anatomy.md), qué tipo de componente usar.

## Requisitos

- Claude Code 2.x; CI valida con la 2.1.282
- Python 3.8+ en el `PATH` para los hooks (sin paquetes de terceros)

## De dónde viene

Hay seis plugins. Otros dos, `java-spring` y `mcp-builder`, se retiraron el
2026-09-25, y `skill-forge` se redujo a su auditor y su registro de
activaciones: en todos los casos de eval, lo retirado puntuaba exactamente lo
mismo que el modelo sin ningún plugin cargado. Por eso `regulated-delivery` es
un hook y nada más. Todas las auditorías y planes detrás de los plugins, con
las mediciones que decidieron cada recorte, están indexados en
[docs/history/](docs/history/README.md).

## Origen

Construido sobre los 22 cursos de [Anthropic Academy](https://academy.claude.com/) (Claude Code, la API de Claude, MCP, despliegue en empresas y AI Fluency) y sobre su aplicación al trabajo diario de backend.

## Seguridad

Los hooks se ejecutan con tus privilegios. [SECURITY.md](SECURITY.md) explica
qué tocan, qué no son y cómo informar de una forma de saltarse uno.

## Licencia

MIT: ver [LICENSE](LICENSE).
