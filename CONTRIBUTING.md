# Contributing to BTCognitive

Thank you for your interest in contributing to the **BTCognitive** AI Bitcoin Market Intelligence & Inference Lab!

## Development Workflow

1. **Fork and Clone the Repository:**
   ```bash
   git clone https://github.com/ashishlabs-23/bitcoin-prediction-lab.git
   cd bitcoin-prediction-lab
   ```

2. **Set up Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Running the Test Suite:**
   ```bash
   pytest -v
   ```

4. **Code Quality & Guidelines:**
   * All quantitative models must strictly avoid lookahead bias and serial correlation.
   * Cross-validation must adhere to **Purged Walk-Forward CV**.
   * Feature engineering additions must be deterministic and leakage-free.

## Submitting Pull Requests

1. Create a feature branch (`git checkout -b feature/my-feature`).
2. Commit your changes with clear, semantic commit messages.
3. Push to your fork and submit a Pull Request to the `main` branch.
