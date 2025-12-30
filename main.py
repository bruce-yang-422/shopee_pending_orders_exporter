#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: main.py
用途: Pipeline 控制主程式
說明: 整體流程控制（符合 EXE 可攜式封裝規格）
     啟動流程順序：
     1. 取得 ROOT_DIR（EXE 所在資料夾 = 專案根目錄）
     2. 確認 config 存在（找不到 → ERROR + log）
     3. 建立必要資料夾（data_raw, temp, data_processed, data_archive, logs）
     4. 開始正式處理：
         - 清理舊 log 檔案（保留最近 48 小時）
         - 清理 temp 目錄中的舊 CSV
         - 載入 Shops Master
         - 掃描 data_raw/ 中的 xlsx
         - 轉換 xlsx → CSV（寫入 temp/）
         - 移動 xlsx 至 data_archive/
         - 從 temp/ 的 CSV 篩選「待出貨」
         - 輸出最終 CSV 至 data_processed/
         - 合併所有結果並排序
     注意：temp/ 中的 CSV 將在下次啟動時清理
Authors: 楊翔志 & AI Collective
Studio: tranquility-base
版本: 1.0 (2025-12-30)
"""

import sys
import logging
import pandas as pd
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from scripts.shops_master_loader import load_shops_master
from scripts.shopee_xlsx_to_csv import xlsx_to_csv
from scripts.filter_pending_from_csv import filter_pending_orders
from scripts.file_utils import (
    calculate_file_hash,
    move_to_archive,
    scan_xlsx_files,
    cleanup_temp_csv,
    cleanup_old_logs
)


def get_root_dir() -> Path:
    """
    取得專案根目錄（EXE 所在資料夾）
    
    處理 PyInstaller 封裝的情況：
    - 如果被封裝成 EXE，使用 sys.executable 的目錄
    - 否則使用 __file__ 的目錄
    
    Returns:
        專案根目錄路徑
    """
    if getattr(sys, 'frozen', False):
        # 被封裝成 EXE 的情況
        # sys.executable 是 EXE 的完整路徑
        return Path(sys.executable).parent
    else:
        # 開發環境：使用 __file__ 的目錄
        return Path(__file__).parent


# 設定 logging
def setup_logging(log_dir: Path):
    """
    設定 logging
    - 檔案：記錄所有 INFO 以上的詳細訊息
    - 終端機：只顯示 WARNING 和 ERROR（簡化輸出）
    
    Args:
        log_dir: log 目錄路徑（必須提供）
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # 清除現有的 handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []
    
    # 檔案 handler：記錄所有 INFO 以上的詳細訊息
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # 終端機 handler：只顯示 WARNING 和 ERROR（簡化輸出）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    
    # 設定 root logger
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return log_file




def main():
    """主程式流程"""
    # 啟動流程順序（符合 EXE 可攜式封裝規格）
    
    # 1. 取得 ROOT_DIR（EXE 所在資料夾 = 專案根目錄）
    root_dir = get_root_dir()
    
    # 設定所有目錄路徑
    config_dir = root_dir / "config"
    data_raw_dir = root_dir / "data_raw"
    data_archive_dir = root_dir / "data_archive"
    temp_dir = root_dir / "temp"
    data_processed_dir = root_dir / "data_processed"
    log_dir = root_dir / "logs"
    
    # 先建立 log 目錄（用於記錄錯誤）
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = setup_logging(log_dir)
    logger = logging.getLogger(__name__)
    
    try:
        # 2. 確認 config 存在
        shops_master_path = config_dir / "A02_Shops_Master - Shops_Master.csv"
        if not shops_master_path.exists():
            error_msg = f"ERROR: 找不到 Shops Master 檔案: {shops_master_path}"
            logger.error(error_msg)
            print(f"ERROR: {error_msg}")
            print(f"請確認 config 目錄中存在 'A02_Shops_Master - Shops_Master.csv' 檔案")
            return
        
        logger.info(f"找到 Shops Master 檔案: {shops_master_path}")
        
        # 3. 建立以下資料夾（不存在才建）
        required_dirs = [
            ("data_raw", data_raw_dir),
            ("temp", temp_dir),
            ("data_processed", data_processed_dir),
            ("data_archive", data_archive_dir),
            ("logs", log_dir)
        ]
        
        for dir_name, dir_path in required_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"確認目錄存在: {dir_name} ({dir_path})")
        
        # 步驟 0: 清理舊 log 檔案（保留最近 48 小時）
        logger.info("步驟 0: 清理舊 log 檔案（保留最近 48 小時）...")
        cleanup_old_logs(log_dir, hours=48, logger_instance=logger)
        
        # 終端機簡化輸出函數
        def print_progress(msg: str):
            """終端機簡化輸出（只顯示重要進度）"""
            print(msg)
            logger.debug(msg)  # 同時記錄到 log
        
        print_progress("開始處理...")
        logger.info("=" * 60)
        logger.info("Shopee Pending Orders Exporter - 開始執行")
        logger.info("=" * 60)
        
        # 4. 開始正式處理
        
        # 步驟 1: 清理 temp 目錄中的舊 CSV（上次執行留下的）
        logger.info("步驟 1: 清理 temp 目錄中的舊 CSV 檔案...")
        cleanup_temp_csv(temp_dir, logger)
        
        # 步驟 2: 載入 Shops Master
        logger.info("步驟 2: 載入 Shops Master...")
        shops_dict = load_shops_master(shops_master_path)
        logger.info(f"成功載入 {len(shops_dict)} 個 Shopee 商店")
        
        # 步驟 3: 掃描 data_raw/ 中的 xlsx（排除已處理的）
        logger.info("步驟 3: 掃描 data_raw/ 中的 xlsx 檔案...")
        data_raw_dir.mkdir(parents=True, exist_ok=True)
        data_archive_dir.mkdir(parents=True, exist_ok=True)
        xlsx_files = scan_xlsx_files(data_raw_dir, data_archive_dir)
        
        if not xlsx_files:
            print_progress("未找到待處理的 xlsx 檔案")
            logger.warning("data_raw/ 中沒有找到 xlsx 檔案")
            return
        
        print_progress(f"找到 {len(xlsx_files)} 個待處理檔案")
        logger.info(f"找到 {len(xlsx_files)} 個 xlsx 檔案")
        
        # 收集所有處理後的 CSV 路徑（用於最後合併）
        processed_csv_paths: List[Path] = []
        
        # 處理每個 xlsx 檔案
        for idx, xlsx_path in enumerate(xlsx_files, 1):
            logger.info("-" * 60)
            logger.info(f"處理檔案: {xlsx_path.name}")
            print_progress(f"[{idx}/{len(xlsx_files)}] 處理: {xlsx_path.name}")
            
            try:
                # 再次檢查檔案是否存在（可能在之前的處理中已被移動）
                if not xlsx_path.exists():
                    logger.warning(f"檔案 {xlsx_path.name} 不存在，可能已被移動，跳過")
                    continue
                
                # 計算檔案 hash（在處理前計算，符合 Content-hash–based Idempotent Processing）
                file_hash = calculate_file_hash(xlsx_path)
                logger.info(f"檔案 hash: {file_hash}")
                
                # 步驟 4: 讀取 xlsx → 轉成全量訂單 CSV（寫入 temp 目錄）
                logger.info("步驟 4: 轉換 xlsx 為 CSV（寫入 temp 目錄）...")
                csv_path = xlsx_to_csv(xlsx_path, output_csv_path=temp_dir / f"{xlsx_path.stem}.csv")
                logger.info(f"成功轉換為: {csv_path.name}")
                
                # 再次檢查檔案是否存在（轉換後可能被其他程序移動）
                if not xlsx_path.exists():
                    logger.warning(f"檔案 {xlsx_path.name} 在轉換後不存在，可能已被移動，跳過移動步驟")
                else:
                    # 步驟 5: 移動 xlsx 至 data_archive/（檔名加上 hash）
                    logger.info("步驟 5: 移動 xlsx 至 data_archive/（檔名加上 hash）...")
                    archive_path = move_to_archive(xlsx_path, data_archive_dir, file_hash)
                    logger.info(f"已移動至: {archive_path.name}")
                
                # 步驟 6: 從 temp 目錄的 CSV 篩選「待出貨」
                logger.info("步驟 6: 從 temp 目錄的 CSV 篩選待出貨訂單...")
                output_path = filter_pending_orders(csv_path, shops_dict, output_path=data_processed_dir / f"pending_orders_{csv_path.stem}.csv")
                logger.info(f"成功輸出: {output_path.name}")
                
                # 收集處理後的 CSV 路徑（用於最後合併）
                if output_path.exists():
                    processed_csv_paths.append(output_path)
                
                # 記錄處理完成（包含 hash，符合 log 行為定義）
                logger.info(f"PROCESSED | {xlsx_path.name} | hash={file_hash} | exported {output_path.name}")
                logger.info(f"✓ 檔案 {xlsx_path.name} 處理完成（CSV 保留在 temp 目錄，下次啟動時清理）")
                print_progress(f"  ✓ 完成")
                
            except Exception as e:
                # 記錄錯誤（包含 hash，符合 log 行為定義）
                # 嘗試取得 hash（如果檔案存在且之前已計算）
                error_hash = "unknown"
                try:
                    if xlsx_path.exists():
                        error_hash = calculate_file_hash(xlsx_path)
                except:
                    pass
                logger.error(f"ERROR | {xlsx_path.name} | hash={error_hash} | {str(e)}", exc_info=True)
                # 根據開發規畫：任何失敗不得移動 xlsx 到 archive
                # 所以這裡不移動檔案，繼續處理下一個
                continue
        
        # 步驟 7: 合併所有處理後的 CSV 並排序
        if processed_csv_paths:
            print_progress("合併所有處理結果...")
            logger.info("=" * 60)
            logger.info("步驟 7: 合併所有處理後的 CSV 並排序...")
            try:
                # 讀取所有 CSV 並合併
                dfs = []
                for csv_path in processed_csv_paths:
                    try:
                        df = pd.read_csv(csv_path, encoding='utf-8-sig')
                        if not df.empty:
                            dfs.append(df)
                            logger.debug(f"讀取 {csv_path.name}: {len(df)} 筆")
                    except Exception as e:
                        logger.warning(f"無法讀取 {csv_path.name}: {e}")
                        continue
                
                if dfs:
                    # 合併所有 DataFrame
                    df_merged = pd.concat(dfs, ignore_index=True)
                    logger.info(f"合併前總計: {len(df_merged)} 筆")
                    
                    # 去重：以「訂單編號」為 key，保留第一個出現的記錄
                    if '訂單編號' in df_merged.columns:
                        original_count = len(df_merged)
                        df_merged = df_merged.drop_duplicates(subset=['訂單編號'], keep='first')
                        if len(df_merged) < original_count:
                            logger.info(f"合併後去重：從 {original_count} 筆減少到 {len(df_merged)} 筆（以訂單編號為 key）")
                    
                    # 排序：按照 分店名稱 > 訂單日期 > 物流公司
                    sort_columns = []
                    if '分店名稱' in df_merged.columns:
                        sort_columns.append('分店名稱')
                    if '訂單日期' in df_merged.columns:
                        sort_columns.append('訂單日期')
                    if '物流公司' in df_merged.columns:
                        sort_columns.append('物流公司')
                    
                    if sort_columns:
                        df_merged = df_merged.sort_values(by=sort_columns, na_position='last')
                        logger.info(f"已按照 {', '.join(sort_columns)} 排序")
                    
                    # 輸出合併後的 CSV
                    merged_output_path = data_processed_dir / f"pending_orders_merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    
                    df_merged.to_csv(merged_output_path, index=False, encoding='utf-8-sig')
                    logger.info(f"成功合併並輸出: {merged_output_path.name} ({len(df_merged)} 筆)")
                    print_progress(f"✓ 合併完成: {merged_output_path.name} ({len(df_merged)} 筆)")
                else:
                    logger.warning("沒有可合併的 CSV 資料")
                    
            except Exception as e:
                logger.error(f"合併 CSV 時發生錯誤: {e}", exc_info=True)
        
        print_progress("處理完成")
        logger.info("=" * 60)
        logger.info("所有檔案處理完成")
        logger.info(f"Log 檔案: {log_file}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"執行過程中發生嚴重錯誤: {e}", exc_info=True)
        print(f"ERROR: {e}")
        raise


if __name__ == "__main__":
    main()

