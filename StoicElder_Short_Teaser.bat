@echo off
cd /d "C:\Users\joema\Desktop\Claude\StoicElderWisdom"
"C:\Users\joema\AppData\Local\Python\pythoncore-3.14-64\python.exe" run_shorts_pipeline.py --count 1 --teaser >> logs\shorts.log 2>&1
