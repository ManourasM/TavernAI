@echo off
echo 📦 Creating virtual environment...
python -m venv venv

echo 🔁 Activating virtual environment...
call venv\Scripts\activate

echo ⬇️ Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo 📚 Downloading spaCy Greek language model...
python -m spacy download el_core_news_sm

echo ✅ Setup complete.
echo To start the server, run:
echo venv\Scripts\activate && uvicorn app.main:app --reload
