New-Item -Path ".env" -ItemType "File" -Value "CMC_API_KEY="
python -m venv venv
./venv/Scripts/activate
pip install -r requirements.txt
echo "Install Complete! "