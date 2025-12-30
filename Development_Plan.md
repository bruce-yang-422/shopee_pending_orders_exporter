# Shopee Pending Orders Exporter  
開發規畫書（Development Plan｜以 Shops Master 為準）

---

## 一、專案目的（Purpose）

本專案旨在建立一套 **可重跑、可追溯、低耦合** 的批次處理工具，用於：

- 將 **Shopee 匯出的 xlsx 訂單檔** 轉換為 CSV
- 以 **CSV 作為後續唯一主檔（Single Source of Truth）**
- 從 CSV 中篩選 **「待出貨」訂單**
- 產出標準化、可直接使用於出貨與核對流程的最終 CSV
- 分店（商店）資訊 **統一由中央主檔（Shops Master）控管**

本專案明確 **不從檔名、不從 Excel 內容自行推導店名**，  
所有店家資訊 **只信任 Shops Master**。

---

## 二、核心設計原則（Design Principles）

1. **Shops Master 為唯一店家權威**
   - 分店名稱、狀態、部門、負責人等
   - 一律來自 `config/A02_Shops_Master - Shops_Master.csv`

2. **shop_id 為唯一鍵**
   - 所有關聯只使用 `shop_id (SHxxxx)`
   - 不以中文店名作為 join key

3. **CSV 為主檔**
   - xlsx 僅用於一次性轉換
   - 所有商業邏輯僅操作 CSV

4. **資料與邏輯解耦**
   - 店家資料：Shops Master
   - 訂單資料：Shopee 匯出
   - 程式只負責「對齊與轉換」

---

## 三、Shops Master 定位與規格

### 檔案位置
```text
config/A02_Shops_Master - Shops_Master.csv
````

### 關鍵欄位（實際使用）

```text
platform      # 平台（Shopee）
shop_id       # 商店代碼（SH0001）
shop_account  # 商店帳號
shop_name     # 商店名稱（正式）
shop_status   # 是否啟用
department
manager
```

### 使用原則

* 僅讀取 `platform = Shopee`
* 僅使用 `shop_status = TRUE`
* `shop_id` 為 **訂單 ↔ 店家** 唯一關聯鍵

---

## 四、資料夾語意（最終定義）

```text
data_raw/        # 工作中資料（僅 xlsx，待處理的原始檔案）
temp/            # 臨時 CSV 檔案（xlsx 轉換後的中間檔案，下次啟動時自動清理）
data_processed/  # 最終結果（pending orders csv）
data_archive/    # 歷史 xlsx（已處理完成的原始檔案）
logs/            # 每次執行紀錄
config/          # 設定檔（Shops Master 等）
```

---

## 五、整體流程設計（Pipeline）

```text
0. 清理舊 log 檔案（保留最近 48 小時）
1. 清理 temp/ 目錄中的舊 CSV（上次執行留下的）
2. 載入 Shops Master（只做一次）
3. 掃描 data_raw/ 中的 xlsx（使用內容雜湊判斷是否已處理）
4. 對每個 xlsx 檔案：
   a. 計算檔案內容雜湊（SHA-256 前 10 碼）
   b. 檢查是否已在 archive 中（避免重複處理）
   c. 讀取 xlsx → 轉成全量訂單 CSV（寫入 temp/）
      - 若 xlsx 中沒有 shop_id 欄位，從檔名提取（格式：_SHxxxx_）
   d. 將 xlsx 移至 data_archive/（檔名加上 hash）
   e. 從 temp/ 讀取 CSV
   f. 由訂單資料取得 shop_id
   g. 使用 shop_id JOIN Shops Master → 取得 shop_name
   h. 篩選「待出貨」訂單
   i. 去重（以「訂單編號」為 key）
   j. 輸出個別 CSV 至 data_processed/
5. 合併所有處理後的 CSV
6. 再次去重（以「訂單編號」為 key）
7. 排序（分店名稱 > 訂單日期 > 物流公司）
8. 輸出合併 CSV 至 data_processed/
9. 寫入 logs

注意：
- temp/ 中的 CSV 將在下次啟動時自動清理
- log 檔案會自動清理超過 48 小時的舊檔案
```

---

## 六、模組責任劃分

### main.py

* Pipeline 控制
* 啟動時清理舊 log 檔案（保留最近 48 小時）
* 啟動時清理 temp/ 目錄中的舊 CSV
* 載入 Shops Master
* 掃描 data_raw/ 資料夾（使用內容雜湊判斷是否已處理）
* 協調各模組執行
* 合併所有處理結果並排序
* 例外處理與 log
* 簡化終端機輸出（詳細資訊只記錄在 log 檔案中）

---

### shops_master_loader.py

* 讀取 `A02_Shops_Master - Shops_Master.csv`
* 回傳 `dict[shop_id] → shop_name / meta`
* 僅處理 Shopee 平台

---

### shopee_xlsx_to_csv.py

* 讀取 Shopee xlsx
* 標準化欄位
* 產生全量訂單 CSV（不篩選）
* 確保輸出包含 `shop_id`
  - 若 xlsx 中沒有 shop_id 欄位，從檔名提取（格式：_SHxxxx_）
* 輸出至 `temp/` 目錄

---

### filter_pending_from_csv.py

* 只讀取 CSV（從 temp/ 目錄）
* 判斷訂單狀態為「待出貨」
* 使用 shop_id JOIN Shops Master 取得 shop_name
* 去重（以「訂單編號」為 key）
* 輸出最終 pending orders CSV 至 data_processed/

---

### file_utils.py

* 檔案雜湊計算（SHA-256 前 10 碼）
* 檔案移動與歸檔（含重試機制）
* 檔案掃描（基於內容雜湊的冪等性處理）
* 目錄清理（temp CSV、舊 log 檔案）

---

### shop_id_extractor.py

* 從 DataFrame 欄位中尋找 shop_id
* 從檔名中提取 shop_id（格式：_SHxxxx_）
* 提供統一的提取介面

---

### column_mapper.py

* 將 Shopee CSV 欄位映射到輸出欄位
* 支援多種欄位名稱變體
* 建立最終輸出 DataFrame

---

## 七、最終 CSV 規格

### 輸出檔案

#### 個別處理結果
- 檔名格式：`pending_orders_<原始檔名>.csv`
- 位置：`data_processed/` 目錄
- 內容：該檔案的待出貨訂單（已去重）

#### 合併結果
- 檔名格式：`pending_orders_merged_YYYYMMDD_HHMMSS.csv`
- 位置：`data_processed/` 目錄
- 內容：所有檔案的待出貨訂單合併（已去重、已排序）

### CSV 欄位規格

```text
分店名稱,訂單日期,訂單編號,物流公司,物流單號,備註
```

### 欄位來源說明

| 欄位   | 來源                                |
| ---- | --------------------------------- |
| 分店名稱 | Shops Master（shop_id → shop_name） |
| 訂單日期 | Shopee CSV（欄位：訂單日期 / 訂單成立日期） |
| 訂單編號 | Shopee CSV（欄位：訂單編號） |
| 物流公司 | Shopee CSV（欄位：**寄送方式**） |
| 物流單號 | Shopee CSV（欄位：**包裹查詢號碼**） |
| 備註   | 系統補充 / 空白                         |

### 資料處理規則

1. **去重**：以「訂單編號」為 key，保留第一個出現的記錄
   - 在個別檔案處理時去重
   - 在合併時再次去重

2. **排序**：合併後的 CSV 按照以下順序排序
   - 第一優先：分店名稱
   - 第二優先：訂單日期
   - 第三優先：物流公司

---

## 八、關鍵注意事項（Critical Notes）

1. **禁止自行解析檔名來推店名**
   - shop_name 永遠以 Shops Master 為準
   - 但允許從檔名提取 shop_id（作為資料欄位，不用於推導店名）

2. **shop_name 永遠以 Shops Master 為準**
   - 所有店名資訊只信任 Shops Master
   - shop_id 為唯一關聯鍵

3. **Shops Master 缺 shop_id → 視為錯誤**
   - 若訂單的 shop_id 在 Shops Master 中找不到，記錄警告但繼續處理

4. **data_processed 不得作為輸入**
   - 只從 temp/ 目錄讀取 CSV

5. **CSV 處理階段不得再讀 xlsx**
   - 所有處理邏輯只操作 CSV

6. **任何失敗不得移動 xlsx 到 archive**
   - 只有成功處理後才移動 xlsx

7. **temp/ 目錄的 CSV 在下次啟動時清理**
   - 不在處理完成後立即刪除
   - 確保可重跑性

---

## 九、重複檔案處理防護設計

### 9.1 實際情境盤點

本系統需要處理以下三種常見的重複檔案情境：

#### 情境 1：人工不小心重複丟檔
- 同一份 xlsx 被多次放入 `data_raw/`
- 檔名完全相同 or 幾乎相同

#### 情境 2：為求保險「全部再丟一次」
- 使用者無法確定哪些已處理
- 直接把整包歷史檔再丟進 `data_raw/`

#### 情境 3：檔名被改過，但內容相同
- 內容 byte-for-byte 相同
- 檔名不同（時間、備註、人為改名）

👉 **共同點**  
> 「**檔名完全不可信**，只能相信檔案內容本身」

### 9.2 解決方案

**唯一可靠的判斷方式：以「檔案內容雜湊（Content Hash）」作為處理唯一識別碼**

只要 **內容相同 → hash 必定相同**  
→ 不論檔名怎麼變，都會被視為「已處理」

**採用方案：Content-hash–based Idempotent Processing**

#### 核心規則（鐵律）

1. **hash 以檔案內容計算**
2. **hash 在任何處理前計算**
3. **是否處理，只看 hash**
4. **檔名僅作為輔助資訊**

### 9.3 完整處理行為定義

#### Step 1：掃描 `data_raw/`
- 找到所有 `.xlsx`
- 不管檔名是否重複、是否奇怪

#### Step 2：計算內容 Hash
- 使用 SHA-256
- 取前 10 碼作為識別

```text
file_hash = SHA256(file_bytes)
```

#### Step 3：比對是否已處理

**判斷條件（任一成立即視為已處理）：**

* `data_archive/` 中存在相同 hash 的檔案
  **或**
* （未來）processed index 中已記錄該 hash

#### Step 4：分流處理（最關鍵）

**✅ Case A：hash 不存在（新內容）**
```text
→ 進行完整處理流程
→ 成功後歸檔（檔名加 hash）
→ 記錄 log = PROCESSED
```

**⏭ Case B：hash 已存在（內容重複）**
```text
→ 不再處理
→ 不再轉 csv
→ 不再歸檔第二份
→ 記錄 log = SKIPPED_DUPLICATE
```

### 9.4 歸檔檔名規範（不可變）

**格式：**
```text
<original_stem>__sha256_<hash10>.xlsx
```

**範例：**
```text
萌寵要當家_SH0001_petboss5566_20251230.xlsx
→
萌寵要當家_SH0001_petboss5566_20251230__sha256_ab93f1c2a3.xlsx
```

### 9.5 解決方案驗證

此設計完美解決上述三種情境：

- **情境 1：同檔重丟** → hash 相同 → skip，archive 不會膨脹
- **情境 2：全部亂丟** → 已處理的 hash 全被擋下，只處理「真正新內容」
- **情境 3：改檔名但內容一樣** → 檔名不同不影響，hash 相同視為同一檔

### 9.6 Log 行為定義（可審計）

```text
PROCESSED | SH0005 | hash=ab93f1c2a3 | exported pending_orders_SH0005_20251230.csv
SKIPPED   | SH0005 | hash=ab93f1c2a3 | duplicate content, already archived
ERROR     | SH0002 | hash=ef41aa90bc | parse failed
```

### 9.7 刻意不採用的方案

| 方法   | 不採用原因    |
| ---- | -------- |
| 檔名比對 | 無法處理改名   |
| 時間戳  | 同內容每次不同  |
| UUID | 無法判斷是否重複 |
| 人工標記 | 不可靠      |

### 9.8 使用保證

未來可以放心這樣使用：

> 「不管有沒有處理到，我就把 *所有* xlsx 都丟進去」

系統會自動做到：
* 不重複處理
* 不污染 archive
* 不產生重複結果

---

## 十、風險與防呆設計

* Shops Master 缺失 → 直接 fail fast
* 重複執行 → 覆寫同名檔案（可重跑）
* 訂單無 shop_id → 從檔名提取，若仍無法取得則記錄錯誤
* 檔案被鎖定 → 重試機制（最多 3 次，遞增等待時間）
* 檔案已存在 → 比較檔案大小和修改時間，相同則跳過
* temp/ 目錄清理 → 每次啟動時自動清理舊 CSV，避免累積
* log 目錄清理 → 每次啟動時自動清理超過 48 小時的舊 log 檔案
* 避免重複處理 → 使用內容雜湊（SHA-256 前 10 碼）判斷是否已處理
* 訂單去重 → 以「訂單編號」為 key，自動去除重複訂單
* 檔案不在 archive 中 → 即使 hash 在本次批次中重複，仍視為未處理並重新處理

---

## 十一、輸出與日誌管理

### 輸出檔案管理

* **個別處理結果**：每個 XLSX 檔案處理後產生對應的 CSV（已去重）
* **合併結果**：所有檔案處理完成後產生合併的 CSV（已去重、已排序）
* **檔案命名**：合併結果使用時間戳記，避免覆蓋

### 日誌管理

* **log 檔案位置**：`logs/processing_YYYYMMDD_HHMMSS.log`
* **自動清理**：每次啟動時自動清理超過 48 小時的舊 log 檔案
* **輸出分離**：
  - 終端機：只顯示重要進度（WARNING 和 ERROR）
  - log 檔案：記錄所有詳細資訊（DEBUG 以上）

### 終端機輸出簡化

終端機只顯示：
- 開始處理...
- 找到 X 個待處理檔案
- [1/5] 處理: 檔案名
-   ✓ 完成
- 合併所有處理結果...
- ✓ 合併完成: 檔名 (X 筆)
- 處理完成

詳細資訊（步驟、hash、檔案路徑等）只記錄在 log 檔案中。

---

## 十二、EXE 可攜式封裝規格

### 12.1 封裝結構

```text
shopee_pending_orders_exporter/
├── config/
│   └── A02_Shops_Master - Shops_Master.csv
└── shopee_pending_orders_exporter.exe
```

### 12.2 核心定義

- **EXE 所在資料夾 = 專案根目錄**
- **不使用**：工作目錄、使用者路徑、_MEIPASS
- 所有路徑計算基於 EXE 所在目錄

### 12.3 啟動流程順序

1. **取得 ROOT_DIR**
   - 使用 `get_root_dir()` 函數
   - 處理 PyInstaller 封裝情況（`sys.frozen`）
   - EXE 環境：使用 `sys.executable` 的目錄
   - 開發環境：使用 `__file__` 的目錄

2. **確認 config 存在**
   - 檢查 `config/A02_Shops_Master - Shops_Master.csv`
   - 找不到 → 直接 ERROR + log + 終止程式

3. **建立必要資料夾**（不存在才建）
   - `data_raw/`
   - `temp/`
   - `data_processed/`
   - `data_archive/`
   - `logs/`

4. **開始正式處理**
   - 執行標準處理流程

### 12.4 使用者操作流程

1. 複製整個資料夾（包含 EXE 和 config）
2. 把 XLSX 丟進 `data_raw/`
3. 點兩下 EXE
4. 去 `data_processed/` 拿結果

### 12.5 技術實作

- **`get_root_dir()` 函數**：統一處理路徑計算
- **所有 scripts 改為接收路徑參數**：不再使用 `__file__` 計算相對路徑
- **錯誤處理**：config 不存在時明確提示並終止

---

## 十三、結論

本專案以 **Shops Master 集中控管 + CSV 為主檔 + 內容雜湊防重複 + 自動去重排序** 為核心策略，
確保店名一致性、流程穩定性、避免重複處理、資料完整性與後續系統整合能力。

此文件為後續實作、維護與擴充的**唯一設計依據**。

