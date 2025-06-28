# light-alerm

1. Nếu chưa có môi trường ảo
python -m venv venv

2. Khởi chạy môi trường ảo
venv\Scripts\activate

3. Cài thư viện yêu cầu
pip install -r requirements.txt

4. Khởi động app
python app.py

5. Build app
pyinstaller --onefile --noconsole app.py --add-data "configs;configs" --add-data "controllers;controllers" --add-data "models;models" --add-data "services;services" --add-data "routes;routes"
