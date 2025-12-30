#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: shops_master_loader.py
用途: 載入 Shops Master 主檔
說明: 讀取 config/A02_Shops_Master - Shops_Master.csv
     僅處理 Shopee 平台且 shop_status = TRUE 的商店
     回傳 shop_id → shop_name 的對應字典
Authors: 楊翔志 & AI Collective
Studio: tranquility-base
版本: 1.0 (2025-12-30)
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional


def load_shops_master(config_path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    """
    載入 Shops Master 主檔
    
    Args:
        config_path: Shops Master CSV 檔案路徑，預設為 config/A02_Shops_Master - Shops_Master.csv
    
    Returns:
        Dict[shop_id, Dict]: 
            {
                'SH0001': {
                    'shop_name': '範例商店名稱',
                    'shop_account': 'example_shop_account',
                    'department': '範例部門',
                    'manager': '範例經理',
                    ...
                },
                ...
            }
    
    Raises:
        FileNotFoundError: 找不到 Shops Master 檔案
        ValueError: Shops Master 檔案格式錯誤或缺少必要欄位
    """
    if config_path is None:
        raise ValueError("config_path 參數必須提供（EXE 可攜式封裝要求）")
    
    if not config_path.exists():
        raise FileNotFoundError(f"Shops Master 檔案不存在: {config_path}")
    
    # 讀取 CSV（第一行是英文欄位名稱，第二行是中文標題，從第三行開始是資料）
    # 先讀取第一行作為欄位名稱，然後跳過第二行中文標題
    df = pd.read_csv(config_path, skiprows=[1])
    
    # 檢查必要欄位
    required_columns = ['platform', 'shop_id', 'shop_name', 'shop_status']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Shops Master 缺少必要欄位: {missing_columns}")
    
    # 過濾：僅 Shopee 平台且 shop_status = TRUE
    # 注意：pandas 會將 'TRUE'/'FALSE' 自動轉換為布林值 True/False
    df_filtered = df[
        (df['platform'] == 'Shopee') & 
        (df['shop_status'] == True)
    ].copy()
    
    if df_filtered.empty:
        raise ValueError("Shops Master 中沒有符合條件的 Shopee 商店（platform='Shopee' 且 shop_status='TRUE'）")
    
    # 轉換為字典：shop_id → 完整資訊
    shops_dict = {}
    for _, row in df_filtered.iterrows():
        shop_id = str(row['shop_id']).strip()
        if not shop_id:
            continue
        
        shops_dict[shop_id] = {
            'shop_name': str(row.get('shop_name', '')).strip(),
            'shop_account': str(row.get('shop_account', '')).strip(),
            'department': str(row.get('department', '')).strip(),
            'manager': str(row.get('manager', '')).strip(),
            'location': str(row.get('location', '')).strip(),
        }
    
    if not shops_dict:
        raise ValueError("Shops Master 中沒有有效的 shop_id")
    
    return shops_dict


def get_shop_name(shops_dict: Dict[str, Dict[str, str]], shop_id: str) -> Optional[str]:
    """
    根據 shop_id 取得 shop_name
    
    Args:
        shops_dict: load_shops_master() 回傳的字典
        shop_id: 商店代碼（如 'SH0001'）
    
    Returns:
        shop_name 或 None（如果找不到）
    """
    shop_info = shops_dict.get(shop_id)
    if shop_info:
        return shop_info.get('shop_name')
    return None


if __name__ == "__main__":
    # 測試用
    try:
        shops = load_shops_master()
        print(f"成功載入 {len(shops)} 個 Shopee 商店")
        print("\n前 5 個商店:")
        for i, (shop_id, info) in enumerate(list(shops.items())[:5]):
            print(f"  {shop_id}: {info['shop_name']}")
    except Exception as e:
        print(f"錯誤: {e}")

