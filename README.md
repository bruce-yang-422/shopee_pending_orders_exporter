# Shopee Pending Orders Exporter

Shopee 待處理訂單導出工具

## 專案簡介

Python-based batch processing tool for converting Shopee order XLSX files to CSV and exporting pending shipment orders.

本專案是一套以 Python 撰寫的自動化批次處理工具，  
用於處理 Shopee 平台匯出的訂單資料。

系統會將 Shopee 後台下載的 **XLSX 訂單檔轉換為 CSV**，  
並依訂單狀態篩選出「**待出貨**」訂單，  
產出可直接用於出貨與核對流程的標準化清單。

> 本專案為去除個資後的公開版本，設計情境以台灣電商實務為主。

### 核心功能

- **自動化處理**：一鍵處理多個 XLSX 檔案，無需手動操作
- **資料去重**：以「訂單編號」為唯一識別碼，自動去除重複訂單
- **資料合併**：將所有處理結果合併成單一 CSV 檔案，方便後續使用
- **智能排序**：按照「分店名稱 > 訂單日期 > 物流公司」自動排序
- **重複檔案防護**：使用內容雜湊（SHA-256）判斷檔案是否已處理，避免重複處理
- **自動清理**：自動清理舊的 log 檔案（保留最近 48 小時）和臨時檔案
- **簡化輸出**：終端機只顯示重要進度，詳細資訊記錄在 log 檔案中

## 專案結構

```text
shopee_pending_orders_exporter/
├── main.py                           # 主程式入口
├── scripts/                          # 核心模組
│   ├── __init__.py
│   ├── shops_master_loader.py       # 載入 Shops Master 主檔
│   ├── shopee_xlsx_to_csv.py        # XLSX 轉 CSV 轉換器
│   ├── filter_pending_from_csv.py  # 待出貨訂單篩選器
│   ├── file_utils.py               # 檔案操作工具（雜湊、歸檔、掃描）
│   ├── shop_id_extractor.py        # shop_id 提取工具
│   └── column_mapper.py            # 欄位映射工具
├── config/                          # 設定檔目錄
│   ├── A02_Shops_Master - Shops_Master.csv  # 商店主檔
│   └── Shops_Master_Template.csv   # Shops Master 範本檔案（參考用）
├── data_raw/                        # 原始 XLSX 檔案（待處理）
├── temp/                            # 臨時 CSV 檔案（自動清理）
├── data_processed/                  # 最終結果（待出貨訂單 CSV）
├── data_archive/                    # 已處理的 XLSX 檔案（歷史歸檔）
├── logs/                            # 執行日誌（自動清理）
├── requirements.txt                 # Python 依賴套件
└── Development_Plan.md              # 詳細設計文件
```

## 環境需求

- **Python**: 3.7 或以上版本
- **作業系統**: Windows / Linux / macOS

## 安裝步驟

### 1. 克隆專案

```bash
git clone https://github.com/bruce-yang-422/shopee_pending_orders_exporter.git
cd shopee_pending_orders_exporter
```

### 2. 建立虛擬環境

```bash
python -m venv .venv
```

### 3. 啟動虛擬環境

**Windows:**
```bash
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### 4. 安裝依賴套件

```bash
pip install -r requirements.txt
```

## 使用方式

### 方式一：Python 腳本執行

1. **準備資料**：將 Shopee 匯出的 XLSX 訂單檔放入 `data_raw/` 目錄

2. **執行程式**：
```bash
python main.py
```

3. **查看結果**：處理完成後，結果會輸出至 `data_processed/` 目錄

4. **查看日誌**：詳細處理過程記錄在 `logs/` 目錄中

### 方式二：EXE 可攜式版本（推薦）

如果已封裝成 EXE 可攜式版本，使用方式更簡單：

1. **複製整個資料夾**（包含 EXE 和 config 目錄）

2. **準備資料**：將 Shopee 匯出的 XLSX 訂單檔放入 `data_raw/` 目錄

3. **執行**：雙擊 `shopee_pending_orders_exporter.exe`

4. **查看結果**：處理完成後，結果會輸出至 `data_processed/` 目錄

**注意事項**：
- EXE 所在資料夾即為專案根目錄
- 請確保 `config/A02_Shops_Master - Shops_Master.csv` 檔案存在
- 程式會自動建立必要的資料夾（data_raw, temp, data_processed, data_archive, logs）
- 如果找不到 config 檔案，程式會顯示錯誤訊息並終止

### 輸出檔案說明

#### 個別處理結果
- **檔名格式**：`pending_orders_<原始檔名>.csv`
- **位置**：`data_processed/` 目錄
- **內容**：該檔案的待出貨訂單（已去重）

#### 合併結果（推薦使用）
- **檔名格式**：`pending_orders_merged_YYYYMMDD_HHMMSS.csv`
- **位置**：`data_processed/` 目錄
- **內容**：所有檔案的待出貨訂單合併（已去重、已排序）
- **排序規則**：分店名稱 > 訂單日期 > 物流公司

### 輸出 CSV 欄位

最終輸出的 CSV 包含以下欄位：

| 欄位 | 說明 | 來源 |
|------|------|------|
| 分店名稱 | 商店名稱 | Shops Master（透過 shop_id 對應） |
| 訂單日期 | 訂單成立日期 | Shopee CSV |
| 訂單編號 | 訂單唯一識別碼 | Shopee CSV（用於去重） |
| 物流公司 | 物流/寄送方式 | Shopee CSV（來源欄位：寄送方式） |
| 物流單號 | 包裹追蹤號碼 | Shopee CSV（來源欄位：包裹查詢號碼） |
| 備註 | 備註資訊 | 系統補充（預設為空） |

## 模組架構

### 核心模組

- **`shops_master_loader.py`**：載入商店主檔，提供 shop_id 與 shop_name 的對應關係
- **`shopee_xlsx_to_csv.py`**：將 XLSX 轉換為 CSV，確保包含 shop_id（可從檔名提取）
- **`filter_pending_from_csv.py`**：篩選「待出貨」訂單並格式化輸出，自動去重

### 工具模組

- **`file_utils.py`**：檔案操作工具
  - 檔案雜湊計算（SHA-256）
  - 檔案移動與歸檔（含重試機制）
  - 檔案掃描（基於內容雜湊的冪等性處理）
  - 目錄清理（temp CSV、舊 log 檔案）
- **`shop_id_extractor.py`**：從檔名或欄位提取 shop_id
- **`column_mapper.py`**：欄位映射與輸出格式化

## 設計特色

### 1. 資料完整性保證

- **Shops Master 為唯一權威**：所有商店資訊統一由中央主檔控管
- **shop_id 為唯一鍵**：所有關聯只使用 shop_id，不以中文店名作為 join key
- **自動去重**：以「訂單編號」為 key，確保資料不重複

### 2. 重複檔案防護

- **內容雜湊判斷**：使用 SHA-256 前 10 碼作為檔案唯一識別
- **冪等性處理**：相同內容的檔案只處理一次，即使檔名不同
- **自動歸檔**：已處理的檔案自動移動至 `data_archive/` 目錄

### 3. 自動化清理

- **temp 目錄**：每次啟動時自動清理舊的 CSV 檔案
- **log 目錄**：自動清理超過 48 小時的舊 log 檔案
- **避免累積**：確保工作目錄保持整潔

### 4. 錯誤處理

- **重試機制**：檔案操作失敗時自動重試（最多 3 次）
- **詳細日誌**：所有處理過程詳細記錄在 log 檔案中
- **失敗保護**：處理失敗的檔案不會移動到 archive，可重新處理

## 依賴套件

```text
et-xmlfile==2.0.0
numpy==2.4.0
openpyxl==3.1.5
pandas==2.3.3
python-dateutil==2.9.0.post0
pytz==2025.2
six==1.17.0
tzdata==2025.3
```

## 注意事項

1. **Shops Master 檔案**：請確保 `config/A02_Shops_Master - Shops_Master.csv` 檔案存在且格式正確
   - 可參考 `config/Shops_Master_Template.csv` 範本檔案了解格式要求
   - 必要欄位：`platform`, `shop_id`, `shop_name`, `shop_status`
   - 僅處理 `platform='Shopee'` 且 `shop_status='TRUE'` 的商店
2. **檔案命名**：XLSX 檔案名稱建議包含 shop_id（格式：`_SHxxxx_`），以便系統自動提取
3. **重複處理**：系統會自動判斷檔案是否已處理，可放心重複放入檔案
4. **日誌檔案**：詳細處理過程請查看 `logs/` 目錄中的 log 檔案

## 詳細文件

完整的設計文件、流程說明和技術細節請參考 [Development_Plan.md](Development_Plan.md)

## 版本資訊

- **版本**：1.0 (2025-12-30)
- **作者**：楊翔志 & AI Collective
- **工作室**：tranquility-base

## 授權

（待補充）
