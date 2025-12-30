#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: shopee_xlsx_to_csv.py
用途: 將 Shopee xlsx 訂單檔轉換為 CSV
說明: 讀取 Shopee xlsx 檔案
     標準化欄位並確保包含 shop_id
     產生全量訂單 CSV（不篩選）
Authors: 楊翔志 & AI Collective
Studio: tranquility-base
版本: 1.0 (2025-12-30)
"""

import pandas as pd
from pathlib import Path
from typing import Optional
import logging

from .shop_id_extractor import extract_shop_id_from_filename, find_shop_id_column

logger = logging.getLogger(__name__)


def xlsx_to_csv(
    xlsx_path: Path,
    output_csv_path: Optional[Path] = None,
    sheet_name: Optional[str] = None
) -> Path:
    """
    將 Shopee xlsx 訂單檔轉換為 CSV
    
    Args:
        xlsx_path: 輸入的 xlsx 檔案路徑
        output_csv_path: 輸出的 CSV 檔案路徑，預設為 data_raw/ 目錄下同名檔案
        sheet_name: Excel 工作表名稱，預設為第一個工作表
    
    Returns:
        輸出 CSV 檔案路徑
    
    Raises:
        FileNotFoundError: xlsx 檔案不存在
        ValueError: xlsx 檔案格式錯誤或缺少必要欄位
    """
    if not xlsx_path.exists():
        raise FileNotFoundError(f"xlsx 檔案不存在: {xlsx_path}")
    
    # 預設輸出路徑（改為 temp 目錄）
    if output_csv_path is None:
        output_dir = Path(__file__).parent.parent / "temp"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_csv_path = output_dir / f"{xlsx_path.stem}.csv"
    
    # 讀取 xlsx
    excel_file = None
    try:
        if sheet_name:
            excel_file = pd.ExcelFile(xlsx_path)
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
        else:
            # 讀取第一個工作表
            excel_file = pd.ExcelFile(xlsx_path)
            df = pd.read_excel(excel_file, sheet_name=excel_file.sheet_names[0])
    except Exception as e:
        raise ValueError(f"無法讀取 xlsx 檔案: {e}")
    finally:
        # 確保 Excel 檔案已關閉
        if excel_file is not None:
            excel_file.close()
    
    if df.empty:
        raise ValueError(f"xlsx 檔案為空: {xlsx_path}")
    
    # 保留原始欄位名稱（不轉為小寫，因為後續處理需要原始中文欄位名稱）
    # 提取 shop_id（優先從欄位，其次從檔名）
    shop_id_col = find_shop_id_column(df.columns)
    
    if shop_id_col:
        # 如果找到現有的 shop_id 欄位，確保不為空
        if df[shop_id_col].isna().all():
            # 如果所有值都為空，嘗試從檔名提取
            extracted_shop_id = extract_shop_id_from_filename(xlsx_path.stem)
            if extracted_shop_id:
                logger.info(f"shop_id 欄位為空，從檔名中提取: {extracted_shop_id}")
                df[shop_id_col] = extracted_shop_id
            else:
                raise ValueError(f"xlsx 檔案中所有訂單的 shop_id 都為空，且無法從檔名提取")
        else:
            # 標準化 shop_id 格式（去除空格，轉為字串）
            df[shop_id_col] = df[shop_id_col].astype(str).str.strip()
        
        # 如果欄位名稱不是 'shop_id'，重新命名為標準名稱
        if shop_id_col != 'shop_id':
            df = df.rename(columns={shop_id_col: 'shop_id'})
    else:
        # 如果找不到 shop_id 欄位，從檔名中提取
        extracted_shop_id = extract_shop_id_from_filename(xlsx_path.stem)
        if extracted_shop_id:
            logger.info(f"從檔名中提取 shop_id: {extracted_shop_id}")
            # 新增 shop_id 欄位到 DataFrame
            df['shop_id'] = extracted_shop_id
        else:
            raise ValueError(f"xlsx 檔案缺少 shop_id 欄位，且檔名中無法提取 shop_id（檔名格式應包含 _SHxxxx_）")
    
    # 儲存為 CSV
    try:
        df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
        logger.info(f"成功轉換: {xlsx_path.name} -> {output_csv_path.name}")
    except Exception as e:
        raise ValueError(f"無法寫入 CSV 檔案: {e}")
    
    return output_csv_path


if __name__ == "__main__":
    # 測試用
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python shopee_xlsx_to_csv.py <xlsx_path> [output_csv_path]")
        sys.exit(1)
    
    xlsx_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    
    try:
        result = xlsx_to_csv(xlsx_path, output_path)
        print(f"轉換成功: {result}")
    except Exception as e:
        print(f"錯誤: {e}")
        sys.exit(1)

