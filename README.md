# DraftKings Multi-Sport Optimizer + Analysis Suite 🏆

**A complete Streamlit-based solution for Daily Fantasy Sports (DFS) optimization, analysis, and AI coaching.**

This tool provides an all-in-one workspace to import DraftKings player data, analyze matchups/value, visualize market inefficiencies, generate winning lineups using an advanced optimization engine, and receive strategic feedback from a local AI Coach (Ollama).

![Dashboard Screenshot](images/dashboard_preview.png)
*(Note: Place your screenshot in `images/dashboard_preview.png`)*

## ✨ Key Features

* **📂 Data Management**: Import CSVs (DKSalaries), Auto-detect downloads, or fetch from Official APIs.
* **📊 Analysis Suite**:
  * **Value Metrics**: Value multipliers, Ceiling projections, and Anomaly detection.
  * **Visualization**: Interactive charts for Salary vs. Projection, Ownership leverage, and Team Stacking heatmaps.
* **🤖 AI Coach (Optional)**:
  * **Slate Summary**: Get an instant overview of the slate.
  * **Strategy**: Ask for GPP/Cash game strategies customized to the current data.
  * **Critique**: Have the AI review your generated lineups for flaws.
  * *(Requires local [Ollama](https://ollama.com/) instance)*
* **⚙️ Optimizer Engine**:
  * **Rule-Driven**: Supports any sport via YAML config (NBA, NFL, MLB, etc.).
  * **Advanced Constraints**: Ownership caps, Stacking rules, Min Ceiling, Max Chalk.
  * **Modes**: Cash (Projection) vs. GPP (EV/Ceiling weighted).
* **📓 Learning Journal**: Auto-log your insights, AI advice, and download your history (JSONL/CSV).

## 🚀 Quickstart (Local)

### Prerequisites

* Python 3.10+
* (Optional) [Ollama](https://ollama.com/) installed and running for AI features.

### Installation

1. **Clone the repository**:

    ```bash
    git clone https://github.com/yourusername/draftkings-optimizer.git
    cd draftkings-optimizer
    ```

2. **Set up virtual environment**:

    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Mac/Linux
    source .venv/bin/activate
    ```

3. **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4. **Run the App**:

    ```bash
    streamlit run src/app.py
    ```

Access the app at `http://localhost:8501`.

## 🐳 Docker Support

Run the application in a container without installing Python locally.

### Option 1: Docker Compose (Recommended)

This method persists your data and logs.

```bash
docker compose up --build
```

Then visit `http://localhost:8501`.

* **Volume Mounting**:
  * `./data`: Place your input CSVs here.
  * `./output`: Generated lineups will be saved here.
  * `./logs`: Your journal is saved here.

### Option 2: Build Manually

```bash
docker build -t dk-optimizer .
docker run -p 8501:8501 -v "%cd%/data:/app/data" -v "%cd%/output:/app/output" dk-optimizer
```

### 🧠 Using AI with Docker

If you have Ollama running on your host machine, the Docker container is configured to connect to it via `http://host.docker.internal:11434`.
Ensure Ollama is running (`ollama serve`).

## ⚠️ Disclaimer

* **Not Financial Advice**: This tool is for educational and research purposes only.
* **No Guarantees**: "Projections" and "Optimization" do not guarantee winning. DFS involves significant risk.
* **Compliance**: Ensure you comply with DraftKings' Terms of Service regarding scripting and automation tools.

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
