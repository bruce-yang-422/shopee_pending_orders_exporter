#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: shop_id_extractor.py
用途: shop_id 提取工具
說明: 從 xlsx 檔案或檔名中提取 shop_id
     - 優先從 xlsx 欄位中尋找
     - 若找不到，從檔名中提取（格式：_SHxxxx_）
Authors: 楊翔志 & AI Collective
Studio: tranquility-base
版本: 1.0 (2025-12-30)
"""

import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def extract_shop_id_from_filename(filename: str) -> Optional[str]:
    """
    從檔名中提取 shop_id（格式：_SHxxxx_）
    
    Args:
        filename: 檔案名稱（不含路徑）
    
    Returns:
        shop_id（如 'SH0004'）或 None
    """
    match = re.search(r'_(SH\d{4})_', filename)
    if match:
        return match.group(1)
    return None


def find_shop_id_column(df_columns) -> Optional[str]:
    """
    在 DataFrame 欄位中尋找 shop_id 欄位
    
    Args:
        df_columns: DataFrame 的 columns（可以是 list 或 Index）
    
    Returns:
        找到的欄位名稱，如果找不到則返回 None
    """
    shop_id_columns = ['shop_id', '商店id', '商店代碼', 'shop code', 'store_id', '商店ID', '商店代碼']
    
    for col in df_columns:
        col_stripped = str(col).strip()
        # 檢查是否匹配任何可能的 shop_id 欄位名稱
        if col_stripped in shop_id_columns or col_stripped.lower() in [c.lower() for c in shop_id_columns]:
            return col
    return None


def extract_shop_id(xlsx_path: Path, df_columns) -> str:
    """
    提取 shop_id（優先從欄位，其次從檔名）
    
    Args:
        xlsx_path: xlsx 檔案路徑
        df_columns: DataFrame 的 columns
    
    Returns:
        shop_id（如 'SH0004'）
    
    Raises:
        ValueError: 無法提取 shop_id
    """
    # 優先從欄位中尋找
    shop_id_col = find_shop_id_column(df_columns)
    if shop_id_col:
        logger.debug(f"找到 shop_id 欄位: {shop_id_col}")
        return shop_id_col
    
    # 若找不到，從檔名中提取
    shop_id = extract_shop_id_from_filename(xlsx_path.stem)
    if shop_id:
        logger.info(f"從檔名中提取 shop_id: {shop_id}")
        return shop_id
    
    # 都找不到，拋出錯誤
    raise ValueError(f"xlsx 檔案缺少 shop_id 欄位，且檔名中無法提取 shop_id（檔名格式應包含 _SHxxxx_）")

