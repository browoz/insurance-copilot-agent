$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONPATH = "$root\.deps;$root\app"
Set-Location $root
python -m streamlit run app\streamlit_app.py --global.developmentMode false --server.address 127.0.0.1 --server.port 8501
