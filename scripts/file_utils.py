#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: file_utils.py
用途: 檔案操作工具模組
說明: 提供檔案相關的通用功能
     - 檔案雜湊計算
     - 檔案移動與歸檔
     - 檔案掃描
     - 目錄清理
Authors: 楊翔志 & AI Collective
Studio: tranquility-base
版本: 1.0 (2025-12-30)
"""

import hashlib
import shutil
import time
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def calculate_file_hash(file_path: Path) -> str:
    """
    計算檔案的 SHA-256 雜湊值
    
    Args:
        file_path: 檔案路徑
    
    Returns:
        檔案內容的 SHA-256 hash（前 10 碼）
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # 分塊讀取，避免大檔案記憶體問題
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()[:10]  # 取前 10 碼


def find_archived_file_by_hash(archive_dir: Path, file_hash: str) -> Optional[Path]:
    """
    在 archive 目錄中尋找具有指定 hash 的檔案
    
    Args:
        archive_dir: archive 目錄路徑
        file_hash: 檔案 hash（10 碼）
    
    Returns:
        找到的檔案路徑，如果不存在則返回 None
    """
    # 搜尋格式：*__sha256_<hash>.xlsx
    pattern = f"*__sha256_{file_hash}.xlsx"
    matches = list(archive_dir.glob(pattern))
    if matches:
        return matches[0]
    return None


def move_to_archive(xlsx_path: Path, archive_dir: Path, file_hash: str, max_retries: int = 3) -> Path:
    """
    將 xlsx 檔案移動到 data_archive/（檔名加上 hash）
    
    Args:
        xlsx_path: 原始 xlsx 檔案路徑
        archive_dir: archive 目錄路徑
        file_hash: 檔案內容 hash（10 碼）
        max_retries: 最大重試次數（處理檔案被鎖定的情況）
    
    Returns:
        移動後的檔案路徑
    
    Note:
        歸檔檔名格式：<original_stem>__sha256_<hash10>.xlsx
        如果檔案已存在（相同 hash），直接覆蓋
    """
    archive_dir.mkdir(parents=True, exist_ok=True)
    # 歸檔檔名格式：<original_stem>__sha256_<hash10>.xlsx
    archive_path = archive_dir / f"{xlsx_path.stem}__sha256_{file_hash}{xlsx_path.suffix}"
    
    # 如果檔案已存在（相同 hash），直接覆蓋（理論上不應該發生，因為掃描階段已過濾）
    if archive_path.exists():
        logger.warning(f"Archive 中已存在相同 hash 的檔案 {archive_path.name}，將覆蓋")
        try:
            archive_path.unlink()
        except Exception as e:
            logger.warning(f"無法刪除舊檔案，將使用臨時檔名: {e}")
            # 如果無法刪除，使用時間戳記（但這不應該發生，因為 hash 已檢查過）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_path = archive_dir / f"{xlsx_path.stem}__sha256_{file_hash}_{timestamp}{xlsx_path.suffix}"
    
    # 重試機制：處理檔案被鎖定的情況
    for attempt in range(max_retries):
        try:
            # 先嘗試複製，然後刪除（更可靠）
            shutil.copy2(str(xlsx_path), str(archive_path))
            # 等待一小段時間確保複製完成
            time.sleep(0.1)
            # 驗證複製成功（檢查檔案是否存在且大小相同）
            if archive_path.exists() and archive_path.stat().st_size == xlsx_path.stat().st_size:
                # 刪除原始檔案
                xlsx_path.unlink()
                logger.info(f"成功移動檔案至 archive: {archive_path.name}")
                return archive_path
            else:
                raise ValueError(f"複製的檔案驗證失敗: {archive_path}")
                
        except PermissionError as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 0.5  # 遞增等待時間
                logger.warning(f"檔案被鎖定，等待 {wait_time:.1f} 秒後重試 ({attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                logger.error(f"無法移動檔案 {xlsx_path.name}：檔案被另一個程序使用")
                raise PermissionError(f"無法移動檔案 {xlsx_path.name}：檔案可能被 Excel 或其他程序開啟，請關閉後重試")
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 0.5
                logger.warning(f"移動檔案時發生錯誤，等待 {wait_time:.1f} 秒後重試: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"移動檔案時發生錯誤: {e}")
                raise
    
    return archive_path


def scan_xlsx_files(data_raw_dir: Path, archive_dir: Path) -> List[Path]:
    """
    掃描 data_raw/ 目錄中的 xlsx 檔案（使用內容雜湊判斷是否已處理）
    
    Args:
        data_raw_dir: data_raw 目錄路徑
        archive_dir: archive 目錄路徑（用於檢查是否已處理）
    
    Returns:
        xlsx 檔案路徑列表（僅包含未處理的檔案）
    
    Note:
        基於 Content-hash–based Idempotent Processing 設計
    """
    xlsx_files = list(data_raw_dir.glob("*.xlsx"))
    xlsx_files.extend(list(data_raw_dir.glob("*.XLSX")))
    
    # 過濾：使用內容雜湊判斷是否已處理
    unprocessed_files: List[Path] = []
    processed_hashes: set[str] = set()  # 追蹤已處理的檔案 hash
    
    for xlsx_path in xlsx_files:
        # 檢查檔案是否仍然存在（可能已被之前的處理移動）
        if not xlsx_path.exists():
            continue
        
        # Step 2: 計算內容 Hash（在任何處理前計算）
        try:
            file_hash = calculate_file_hash(xlsx_path)
            logger.debug(f"檔案 {xlsx_path.name} 的 hash: {file_hash}")
        except Exception as e:
            logger.error(f"無法計算檔案 {xlsx_path.name} 的 hash: {e}")
            continue
        
        # Step 3: 比對是否已處理（檢查 archive 中是否有相同 hash）
        archived_file = find_archived_file_by_hash(archive_dir, file_hash)
        if archived_file:
            # Case B: hash 已存在（內容重複）
            logger.info(f"SKIPPED | {xlsx_path.name} | hash={file_hash} | duplicate content, already archived as {archived_file.name}")
            # 刪除 data_raw 中的重複檔案
            try:
                xlsx_path.unlink()
                logger.info(f"已刪除重複檔案: {xlsx_path.name}")
            except Exception as e:
                logger.warning(f"無法刪除重複檔案 {xlsx_path.name}: {e}")
            # 不加入 unprocessed_files，直接跳過
            continue
        
        # 檢查是否已在本次處理中處理過（避免同一批次重複）
        if file_hash in processed_hashes:
            # 檢查是否在 archive 中
            archived_file = find_archived_file_by_hash(archive_dir, file_hash)
            if archived_file:
                # 如果已在 archive 中，視為已處理，刪除重複檔案
                logger.info(f"SKIPPED | {xlsx_path.name} | hash={file_hash} | duplicate content, already archived as {archived_file.name}")
                try:
                    xlsx_path.unlink()
                    logger.info(f"已刪除重複檔案: {xlsx_path.name} (已在 archive 中)")
                except Exception as e:
                    logger.warning(f"無法刪除重複檔案 {xlsx_path.name}: {e}")
                # 不加入 unprocessed_files，直接跳過
                continue
            else:
                # 如果不在 archive 中，視為未處理，繼續處理（可能是第一次處理失敗）
                logger.warning(f"檔案 {xlsx_path.name} 的 hash 在本次批次中重複，但不在 archive 中，視為未處理並重新處理")
                # 繼續執行，將檔案加入處理列表
        
        # Case A: hash 不存在（新內容）
        # 先加入 hash 到 processed_hashes，避免後續重複檔案被加入
        processed_hashes.add(file_hash)
        # 再加入檔案到待處理列表（再次確認檔案存在）
        if xlsx_path.exists():
            unprocessed_files.append(xlsx_path)
        else:
            logger.warning(f"檔案 {xlsx_path.name} 在加入列表前已不存在，跳過")
    
    # 最後過濾：只返回仍然存在的檔案
    existing_files = [f for f in unprocessed_files if f.exists()]
    if len(existing_files) < len(unprocessed_files):
        logger.warning(f"過濾掉 {len(unprocessed_files) - len(existing_files)} 個已不存在的檔案")
    
    return sorted(existing_files)


def cleanup_temp_csv(temp_dir: Path, logger_instance: Optional[logging.Logger] = None):
    """
    清理 temp 目錄中的舊 CSV 檔案（上次執行留下的）
    
    Args:
        temp_dir: temp 目錄路徑
        logger_instance: logger 物件（可選，預設使用模組 logger）
    """
    if logger_instance is None:
        logger_instance = logger
    
    temp_dir.mkdir(parents=True, exist_ok=True)
    csv_files = list(temp_dir.glob("*.csv"))
    
    if csv_files:
        logger_instance.info(f"清理 temp 目錄中的 {len(csv_files)} 個舊 CSV 檔案...")
        for csv_file in csv_files:
            try:
                csv_file.unlink()
                logger_instance.debug(f"已刪除: {csv_file.name}")
            except Exception as e:
                logger_instance.warning(f"無法刪除 {csv_file.name}: {e}")
        logger_instance.info("temp 目錄清理完成")
    else:
        logger_instance.debug("temp 目錄中沒有需要清理的 CSV 檔案")


def cleanup_old_logs(log_dir: Path, hours: int = 48, logger_instance: Optional[logging.Logger] = None):
    """
    清理 log 目錄中超過指定小時數的舊 log 檔案
    
    Args:
        log_dir: log 目錄路徑
        hours: 保留的小時數（預設 48 小時）
        logger_instance: logger 物件（可選，預設使用模組 logger）
    """
    if logger_instance is None:
        logger_instance = logger
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 計算截止時間
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    # 取得所有 .log 檔案
    log_files = list(log_dir.glob("*.log"))
    
    if not log_files:
        logger_instance.debug("log 目錄中沒有 log 檔案")
        return
    
    deleted_count = 0
    for log_file in log_files:
        try:
            # 取得檔案的修改時間
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            # 如果檔案修改時間早於截止時間，則刪除
            if file_mtime < cutoff_time:
                log_file.unlink()
                deleted_count += 1
                logger_instance.debug(f"已刪除舊 log 檔案: {log_file.name} (修改時間: {file_mtime.strftime('%Y-%m-%d %H:%M:%S')})")
        except Exception as e:
            logger_instance.warning(f"無法刪除 log 檔案 {log_file.name}: {e}")
    
    if deleted_count > 0:
        logger_instance.info(f"清理完成：刪除了 {deleted_count} 個超過 {hours} 小時的舊 log 檔案")
    else:
        logger_instance.debug(f"沒有需要清理的舊 log 檔案（保留最近 {hours} 小時）")

