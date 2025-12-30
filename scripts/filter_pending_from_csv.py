#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: filter_pending_from_csv.py
用途: 從 CSV 中篩選「待出貨」訂單
說明: 只讀取 CSV（不讀 xlsx）
     判斷訂單狀態為「待出貨」
     輸出最終 pending orders CSV
Authors: 楊翔志 & AI Collective
Studio: tranquility-base
版本: 1.0 (2025-12-30)
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict
import logging

from .column_mapper import map_shopee_columns_to_output, build_output_dataframe

logger = logging.getLogger(__name__)


def filter_pending_orders(
    csv_path: Path,
    shops_dict: Dict[str, Dict[str, str]],
    output_path: Optional[Path] = None
) -> Path:
    """
    從 CSV 中篩選「待出貨」訂單
    
    Args:
        csv_path: 輸入的 CSV 檔案路徑
        shops_dict: load_shops_master() 回傳的商店字典
        output_path: 輸出的 CSV 檔案路徑，預設為 data_processed/ 目錄下
    
    Returns:
        輸出 CSV 檔案路徑
    
    Raises:
        FileNotFoundError: CSV 檔案不存在
        ValueError: CSV 檔案格式錯誤或缺少必要欄位
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV 檔案不存在: {csv_path}")
    
    # 預設輸出路徑
    if output_path is None:
        output_dir = Path(__file__).parent.parent / "data_processed"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"pending_orders_{csv_path.stem}.csv"
    
    # 讀取 CSV
    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except UnicodeDecodeError:
        # 嘗試其他編碼
        df = pd.read_csv(csv_path, encoding='big5')
    
    if df.empty:
        raise ValueError(f"CSV 檔案為空: {csv_path}")
    
    # 保留原始欄位名稱（不轉為小寫，因為欄位名稱可能是中文）
    df.columns = df.columns.str.strip()
    
    # 檢查必要欄位（shop_id 應該已經在 xlsx_to_csv 中處理過）
    if 'shop_id' not in df.columns:
        raise ValueError(f"CSV 檔案缺少 shop_id 欄位: {csv_path}")
    
    # 標準化 shop_id
    df['shop_id'] = df['shop_id'].astype(str).str.strip()
    
    # 尋找訂單狀態欄位（常見的 Shopee 訂單狀態欄位名稱）
    status_columns = ['訂單狀態', 'order_status', 'order status', 'status', '狀態']
    status_col = None
    for col in df.columns:
        col_stripped = str(col).strip()
        if col_stripped in status_columns or col_stripped.lower() in [c.lower() for c in status_columns]:
            status_col = col
            break
    
    if status_col is None:
        raise ValueError(f"CSV 檔案缺少訂單狀態欄位（可能的欄位名稱: {status_columns}）")
    
    # 篩選「待出貨」訂單
    # 常見的「待出貨」狀態值（根據實際 Shopee 匯出格式調整）
    pending_statuses = [
        '待出貨',
        '待處理',
        'pending',
        '待出貨中',
        '待發貨',
        '待寄出',
        '待出貨（待處理）',
    ]
    
    # 轉為小寫進行比對（不區分大小寫）
    df[status_col] = df[status_col].astype(str).str.strip()
    pending_mask = df[status_col].str.lower().isin([s.lower() for s in pending_statuses])
    df_pending = df[pending_mask].copy()
    
    if df_pending.empty:
        logger.warning(f"CSV 中沒有待出貨訂單: {csv_path}")
        # 仍然建立空檔案
        df_pending = pd.DataFrame()
    else:
        logger.info(f"找到 {len(df_pending)} 筆待出貨訂單")
    
    # 使用 shop_id 對應 shop_name
    df_pending['shop_name'] = df_pending['shop_id'].apply(
        lambda x: shops_dict.get(x, {}).get('shop_name', '') if x in shops_dict else ''
    )
    
    # 檢查是否有 shop_id 找不到對應的 shop_name
    missing_shops = df_pending[df_pending['shop_name'] == '']['shop_id'].unique()
    if len(missing_shops) > 0:
        logger.warning(f"以下 shop_id 在 Shops Master 中找不到: {list(missing_shops)}")
    
    # 準備最終輸出欄位
    # 根據開發規畫，最終 CSV 欄位為：分店名稱,訂單日期,訂單編號,物流公司,物流單號,備註
    
    # 使用 column_mapper 進行欄位映射
    column_mapping = map_shopee_columns_to_output(df_pending)
    
    # 建立最終輸出 DataFrame
    df_output = build_output_dataframe(
        df_pending=df_pending,
        shop_name_series=df_pending['shop_name'],
        column_mapping=column_mapping
    )
    
    # 去重：以「訂單編號」為 key，保留第一個出現的記錄
    if not df_output.empty and '訂單編號' in df_output.columns:
        original_count = len(df_output)
        df_output = df_output.drop_duplicates(subset=['訂單編號'], keep='first')
        if len(df_output) < original_count:
            logger.info(f"去重：從 {original_count} 筆減少到 {len(df_output)} 筆（以訂單編號為 key）")
    
    # 儲存為 CSV
    try:
        df_output.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"成功輸出待出貨訂單: {output_path.name} ({len(df_output)} 筆)")
    except Exception as e:
        raise ValueError(f"無法寫入 CSV 檔案: {e}")
    
    return output_path


if __name__ == "__main__":
    # 測試用
    import sys
    from .shops_master_loader import load_shops_master
    
    if len(sys.argv) < 2:
        print("用法: python filter_pending_from_csv.py <csv_path> [output_path]")
        sys.exit(1)
    
    csv_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    try:
        shops = load_shops_master()
        result = filter_pending_orders(csv_path, shops, output_path)
        print(f"篩選成功: {result}")
    except Exception as e:
        print(f"錯誤: {e}")
        sys.exit(1)

