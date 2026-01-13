# DraftKings Multi-Sport Optimizer + AI Journal

A professional-grade DFS (Daily Fantasy Sports) optimizer and analysis suite for DraftKings.
Includes a Streamlit-based UI, Lineup Optimizer, and AI-powered "Coaching" features using local LLMs (Ollama).

## 🚀 Features

- **Multi-Sport Support**: NFL, NBA, MLB, NHL (extensible rule engine).
- **Lineup Optimizer**: Generate up to 150 lineups with customizable constraints (Overlap, Stacking, Groups).
- **Advanced Analysis**:
  - Value & Ceiling Projections
  - Ownership vs. Leverage Analysis
  - Correlation Heatmaps
  - EV (Expected Value) Calculations for GPP
- **AI Coach (Ollama)**:
  - 📝 **Slate Summary**: Get a quick breakdown of the slate.
  - 🔍 **Edge Finder**: Identify potential market inefficiencies.
  - 👮 **Lineup Critique**: AI reviews your generated lineups for flaws.
  - 📓 **Learning Journal**: Auto-tracks your hypothesis and results in `data/journal.jsonl`.
- **Multi-Language**: Switch between English and Japanese UI/AI outputs.

## 🛠 Prerequisites

- **Python**: 3.10+
- **Docker** (Optional, for containerized run)
- **Ollama** (Optional, for AI features)
  - Recommended Model: `llama3.1` or `mistral`

## 📦 Installation & Local Run

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/dk-multi-sport-optimizer.git
   cd dk-multi-sport-optimizer
   ```

2. **Setup Virtual Environment**

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Run Streamlit App**

   ```bash
   streamlit run src/app.py
   ```

   Open <http://localhost:8501> in your browser.

## 🐳 Docker Usage

### Method 1: Docker Compose (Recommended)

```bash
docker compose up --build
```

- Data Persistence: `data/`, `output/`, and `logs/` are mounted locally.

### Method 2: Clean Docker Run

```bash
docker build -t dk-optimizer .
docker run -p 8501:8501 -v $(pwd)/data:/app/data dk-optimizer
```

## 🧠 AI Setup (Ollama)

To use the "AI Coach" tab:

1. Install [Ollama](https://ollama.com/).
2. Pull a model: `ollama pull llama3.1:8b`
3. Run the server: `ollama serve`
4. In the App, go to **AI Coach** tab and ensure the model name matches (default: `llama3.1:8b`).

> **Note**: If Ollama is not detected, AI buttons will be disabled, but the Optimizer works fine.

## 📂 Data Input

1. **DK Salaries**: Upload the `DKSalaries.csv` derived from DraftKings.
2. **Ownership (Optional)**: Upload a CSV with player ownership projections for GPP analysis.
3. **API (Optional)**: Configure `configs/sources.yaml` to fetch from external APIs.

## ⚠️ Disclaimer

This software is for **educational and research purposes only**.
DFS involves financial risk. There is no guarantee of profit. Use responsibly.

## 📄 License

MIT License.
