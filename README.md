# shopee_pending_orders_exporter

Shopee 待處理訂單導出工具

## 專案簡介

本專案用於導出 Shopee 平台的待處理訂單資料。將 Shopee 匯出的 XLSX 訂單檔轉換為 CSV，並篩選出「待出貨」訂單，產出標準化的出貨清單。

## 專案結構

```
shopee_pending_orders_exporter/
├── main.py                    # 主程式入口
├── scripts/                   # 核心模組
│   ├── shops_master_loader.py      # 載入 Shops Master
│   ├── shopee_xlsx_to_csv.py      # XLSX 轉 CSV
│   ├── filter_pending_from_csv.py # 篩選待出貨訂單
│   ├── file_utils.py              # 檔案操作工具
│   ├── shop_id_extractor.py       # shop_id 提取工具
│   └── column_mapper.py           # 欄位映射工具
├── config/                    # 設定檔
│   └── A02_Shops_Master - Shops_Master.csv
├── data_raw/                 # 原始 XLSX 檔案（待處理）
├── temp/                     # 臨時 CSV 檔案
├── data_processed/           # 最終結果（待出貨訂單 CSV）
├── data_archive/             # 已處理的 XLSX 檔案
└── logs/                     # 執行日誌
```

## 環境需求

- Python 3.x

## 安裝步驟

1. 克隆專案：
```bash
git clone https://github.com/bruce-yang-422/shopee_pending_orders_exporter.git
cd shopee_pending_orders_exporter
```

2. 建立虛擬環境：
```bash
python -m venv .venv
```

3. 啟動虛擬環境：
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

4. 安裝依賴套件：
```bash
pip install -r requirements.txt
```

## 使用方式

1. 將 Shopee 匯出的 XLSX 訂單檔放入 `data_raw/` 目錄
2. 執行主程式：
```bash
python main.py
```
3. 處理完成後，結果會輸出至 `data_processed/` 目錄：
   - 個別檔案的處理結果：`pending_orders_<檔名>.csv`
   - 合併後的完整結果：`pending_orders_merged_YYYYMMDD_HHMMSS.csv`（已去重並排序）
4. 原始 XLSX 檔案會自動移動至 `data_archive/` 目錄

## 功能特色

- **自動去重**：以「訂單編號」為 key，自動去除重複訂單
- **合併輸出**：所有處理結果會合併成一個 CSV 檔案
- **自動排序**：按照「分店名稱 > 訂單日期 > 物流公司」排序
- **重複檔案防護**：使用內容雜湊（SHA-256）判斷是否已處理，避免重複處理
- **自動清理**：自動清理舊的 log 檔案（保留最近 48 小時）和 temp 目錄
- **簡化輸出**：終端機只顯示重要進度，詳細資訊記錄在 log 檔案中

## 模組說明

### 核心模組
- **shops_master_loader.py**: 載入商店主檔，提供 shop_id 與 shop_name 對應
- **shopee_xlsx_to_csv.py**: 將 XLSX 轉換為 CSV，確保包含 shop_id
- **filter_pending_from_csv.py**: 篩選「待出貨」訂單並格式化輸出

### 工具模組
- **file_utils.py**: 檔案操作（雜湊計算、歸檔、掃描、log 清理）
- **shop_id_extractor.py**: 從檔名或欄位提取 shop_id
- **column_mapper.py**: 欄位映射與輸出格式化

## 輸出檔案說明

### 個別處理結果
每個 XLSX 檔案處理後會產生對應的 CSV：
- 檔名格式：`pending_orders_<原始檔名>.csv`
- 位置：`data_processed/` 目錄
- 內容：該檔案的待出貨訂單（已去重）

### 合併結果
所有檔案處理完成後會產生合併的 CSV：
- 檔名格式：`pending_orders_merged_YYYYMMDD_HHMMSS.csv`
- 位置：`data_processed/` 目錄
- 內容：所有檔案的待出貨訂單合併（已去重、已排序）
- 排序規則：分店名稱 > 訂單日期 > 物流公司

詳細設計文件請參考 [Development_Plan.md](Development_Plan.md)

## 依賴套件

- et-xmlfile==2.0.0
- numpy==2.4.0
- openpyxl==3.1.5
- pandas==2.3.3
- python-dateutil==2.9.0.post0
- pytz==2025.2
- six==1.17.0
- tzdata==2025.3

## 授權

（待補充）

## 作者

- bruce-yang-422
