# Proyek Analisis Data: Air Quality Dataset (Beijing Multi-Site)

## Struktur
```
submission
├── dashboard
│   ├── main_data.csv.gz   # data bersih (hasil notebook)
│   └── dashboard.py
├── data
│   └── PRSA_Data_20130301-20170228/*.csv   # 12 file stasiun
├── Proyek_Analisis_Data.ipynb
├── README.md
├── requirements.txt
└── url.txt
```

## Setup environment
```
python -m venv venv
venv\Scripts\activate        # Windows  (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
```

## Menjalankan dashboard
```
cd submission
streamlit run dashboard/dashboard.py
```

## Catatan
- `main_data.csv.gz` dihasilkan oleh sel terakhir bagian analisis di notebook (jalankan notebook dari folder `submission`).
- Koordinat stasiun pada peta adalah perkiraan, karena tidak tersedia di dataset.
- Untuk deploy ke Streamlit Cloud: push folder ke GitHub, pilih `dashboard/dashboard.py` sebagai main file, lalu isi URL di `url.txt`.
