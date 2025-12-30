#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: column_mapper.py
用途: 欄位映射工具
說明: 提供 Shopee CSV 欄位到輸出欄位的映射功能
     - 尋找對應的欄位名稱（支援多種變體）
     - 建立最終輸出 DataFrame
Authors: 楊翔志 & AI Collective
Studio: tranquility-base
版本: 1.0 (2025-12-30)
"""

import pandas as pd
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def find_column(df_columns, candidate_names: list[str]) -> Optional[str]:
    """
    在 DataFrame 欄位中尋找匹配的欄位名稱
    
    Args:
        df_columns: DataFrame 的 columns
        candidate_names: 候選欄位名稱列表
    
    Returns:
        找到的欄位名稱，如果找不到則返回 None
    """
    for col in df_columns:
        col_stripped = str(col).strip()
        if col_stripped in candidate_names or col_stripped.lower() in [c.lower() for c in candidate_names]:
            return col
    return None


def map_shopee_columns_to_output(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """
    將 Shopee CSV 欄位映射到輸出欄位
    
    Args:
        df: 輸入的 DataFrame
    
    Returns:
        欄位映射字典：{輸出欄位名稱: 來源欄位名稱或None}
    """
    mapping = {}
    
    # 訂單日期欄位
    date_columns = ['訂單日期', '訂單成立日期', 'order_date', 'order date', '日期', 'date']
    mapping['訂單日期'] = find_column(df.columns, date_columns)
    
    # 訂單編號欄位
    order_id_columns = ['訂單編號', 'order_id', 'order id', '訂單id', 'order_sn']
    mapping['訂單編號'] = find_column(df.columns, order_id_columns)
    
    # 物流公司欄位（對應來源的"寄送方式"）
    logistics_columns = ['寄送方式', '物流公司', 'logistics_company', 'logistics company', '物流', 'shipping_company', '出貨方式']
    mapping['物流公司'] = find_column(df.columns, logistics_columns)
    
    # 物流單號欄位（對應來源的"包裹查詢號碼"）
    tracking_columns = ['包裹查詢號碼', '物流單號', 'tracking_number', 'tracking number', '追蹤號碼', 'tracking_id', '追蹤編號']
    mapping['物流單號'] = find_column(df.columns, tracking_columns)
    
    return mapping


def build_output_dataframe(
    df_pending: pd.DataFrame,
    shop_name_series: pd.Series,
    column_mapping: Dict[str, Optional[str]]
) -> pd.DataFrame:
    """
    建立最終輸出 DataFrame
    
    Args:
        df_pending: 篩選後的待出貨訂單 DataFrame
        shop_name_series: 分店名稱 Series（已透過 shop_id 對應）
        column_mapping: 欄位映射字典
    
    Returns:
        最終輸出的 DataFrame
    """
    output_data = {
        '分店名稱': shop_name_series,
    }
    
    # 根據映射建立輸出欄位
    for output_col, source_col in column_mapping.items():
        if source_col and source_col in df_pending.columns:
            output_data[output_col] = df_pending[source_col]
        else:
            # 建立與 DataFrame 長度相同的空字串 Series
            output_data[output_col] = pd.Series([''] * len(df_pending), dtype=str)
            if output_col != '備註':  # 備註欄位預設為空，不需要警告
                logger.warning(f"找不到{output_col}欄位（來源欄位: {source_col}）")
    
    # 備註欄位（空白或系統補充）
    output_data['備註'] = pd.Series([''] * len(df_pending), dtype=str)
    
    df_output = pd.DataFrame(output_data)
    
    # 重新排列欄位順序
    column_order = ['分店名稱', '訂單日期', '訂單編號', '物流公司', '物流單號', '備註']
    df_output = df_output[column_order]
    
    return df_output

