# Release Notes

## v0.1.0 (Initial Release)

### 🎉 Key Features

- **Core Optimizer**: Solves for max projection or GPP/EV using `pulp`.
- **Streamlit UI**: 7-Tab interface for Data, Analysis, visualiztion, AI, Optimization, Results, and Journal.
- **AI Integration**: Local LLM support via Ollama for critique and strategy.
- **Journaling**: `journal.jsonl` tracks your thought process.
- **Docker Support**: Full containerization with `docker-compose`.

### 🔧 Changes

- Standardized directory structure (`src/`, `configs/`, `rules/`).
- Added robust error handling for missing data.
- Implemented `English` / `Japanese` language switching.

### 🐛 Known Issues

- Large slates (1000+ players) may take >10s to optimize large sets of lineups without a commercial solver.
- AI features require a local Ollama instance (no remote API fallback yet).

### 🚀 Next Steps

- Commercial Solver integration (Gurobi/CPLEX) support.
- API endpoints for headless optimization.
- Enhanced Backtesting module.

## How to Release

```bash
git tag v0.1.0
git push origin v0.1.0
```
