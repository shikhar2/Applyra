#!/usr/bin/env bash
set -e

echo "🚀 Applyra Setup"
echo "=================="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3.10+ required"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PYTHON_VERSION"

# Check Node
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 18+ required"
    exit 1
fi
echo "✓ Node $(node --version)"

# Create venv
echo ""
echo "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install backend deps
echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r backend/requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium
playwright install-deps chromium 2>/dev/null || true

# Install frontend deps
echo "Installing frontend dependencies..."
cd frontend && npm install --silent && cd ..

# Create .env if missing
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  Created .env from template."
    echo "   Edit .env and add your ANTHROPIC_API_KEY before running."
fi

# Create data directories
mkdir -p data/resumes

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your API key:"
echo "     ANTHROPIC_API_KEY=sk-ant-..."
echo ""
echo "  2. Start the backend:"
echo "     source venv/bin/activate"
echo "     uvicorn backend.main:app --reload --port 8000"
echo ""
echo "  3. Start the frontend (new terminal):"
echo "     cd frontend && npm run dev"
echo ""
echo "  4. Open http://localhost:5173"
echo ""
echo "  5. Upload your resume → Create a job profile → Run search!"
