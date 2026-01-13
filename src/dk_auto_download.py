#!/usr/bin/env python3
r"""
DraftKings DKSalaries.csv 自動ログイン & 自動ダウンロード（Playwright, Python）

セットアップ:
  pip install playwright python-dotenv
  playwright install chromium
  プロジェクト直下に .env を置く:
    DK_EMAIL=あなたのメール
    DK_PASSWORD=あなたのパスワード

実行例:
  python src/dk_auto_download.py --sport MLB --outdir data/raw/MLB --headful
  python src/dk_auto_download.py --sport NBA --outdir data/raw/NBA --headful --max-retries 3
  # 画面上の「Download/Export/CSV」候補を列挙する診断:
  python src/dk_auto_download.py --sport MLB --outdir data/raw/MLB --headful --debug-scan
"""
from __future__ import annotations
import os
import sys
import time
import hashlib
import argparse
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

# -------------------- URL --------------------
DK_HOME_URL  = "https://www.draftkings.com/"
DK_LOBBY_URL = "https://www.draftkings.com/lobby"
DK_LOGIN_URL = "https://www.draftkings.com/account/sitelogin?returnurl=/lobby"

# -------------------- 画面セレクタ候補 --------------------
# 入力欄は候補リストから最初に見つかったものを使う（UI差分耐性）
EMAIL_CANDIDATES: List[str] = [
    "input[type=\"email\"]",
    "input[name='email']",
    "input[id='email']",
    "input[name*='user']",
    "input[id*='user']",
]
PASS_CANDIDATES: List[str] = [
    "input[type=\"password\"]",
    "input[name='password']",
    "input[id='password']",
]
LOGIN_SUBMIT_SEL = "button:has-text('Log In'), button:has-text('Sign In'), [type='submit']"

# 2FA
TWOFA_INPUTS: List[str] = [
    "input[type='tel']",
    "input[name*='code']",
    "input[name*='otp']",
]
TWOFA_SUBMITS: List[str] = [
    "button:has-text('Verify')",
    "button:has-text('Submit')",
]

# CSV/Export ボタン候補（必要に応じて追加）
CSV_BUTTON_CANDIDATES: List[str] = [
    "text=Download CSV",
    "text=Download DKSalaries.csv",
    "text=Download Players List",
    "text=Download Player List",
    "text=Export CSV",
    "text=Export to CSV",
    "button:has-text('CSV')",
    "a:has-text('CSV')",
]

# コンテスト詳細に入る候補（トップの PLAY NOW/ENTER 優先）
DETAIL_LINK_CANDIDATES_TOP: List[str] = [
    "text=PLAY NOW",
    "text=Enter",
    "button:has-text('PLAY NOW')",
    "button:has-text('Enter')",
    "[aria-label*='Play Now']",
    "[data-testid*='play-now']",
]
DETAIL_LINK_CANDIDATES_FALLBACK: List[str] = [
    "a[href*='contest']",
    "a[href*='/draft/']",
    "[role='link']",
    "a:has-text('Contest')",
    "a:has-text('Details')",
    "text=Details",
    "text=Contest",
    "text=View",
    "button:has-text('Details')",
]

# -------------------- ユーティリティ --------------------
def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def is_duplicate(tmp_file: Path, outdir: Path) -> bool:
    new_hash = sha256_of(tmp_file)
    for p in outdir.glob('*.csv'):
        try:
            if sha256_of(p) == new_hash:
                return True
        except Exception:
            continue
    return False

def find_first(page, selectors: List[str], timeout_ms: int = 15000):
    """候補セレクタを順に小さいタイムアウトで探す"""
    start = time.time()
    for sel in selectors:
        try:
            el = page.wait_for_selector(sel, timeout=2000)
            if el:
                return el
        except Exception:
            pass
        if time.time() - start > timeout_ms / 1000.0:
            break
    return None

# -------------------- 2FA --------------------
def maybe_handle_twofa(page, timeout_ms: int = 8000) -> None:
    try:
        inp = None
        for sel in TWOFA_INPUTS:
            try:
                inp = page.query_selector(sel)
                if inp:
                    break
            except Exception:
                pass
        if not inp:
            inp = page.wait_for_selector(", ".join(TWOFA_INPUTS), timeout=timeout_ms)
    except PWTimeoutError:
        return  # 2FAなし
    try:
        code = input("Two-Factor Code (2FA) を入力してください: ").strip()
        if not code:
            log("2FAコードが空です。スキップします。")
            return
        inp.fill(code)
        clicked = False
        for sel in TWOFA_SUBMITS:
            btn = page.query_selector(sel)
            if btn:
                btn.click()
                clicked = True
                break
        if not clicked:
            inp.press("Enter")
        page.wait_for_load_state("networkidle", timeout=15000)
        log("2FA送信完了")
    except Exception as e:
        log(f"2FA処理で例外: {e}")

# -------------------- 画面遷移/ダウンロード --------------------
def open_any_contest_detail(page) -> bool:
    # 0) PLAY NOW / ENTER を優先（トップのヒーロー/カード）
    for sel in DETAIL_LINK_CANDIDATES_TOP:
        try:
            btn = page.query_selector(sel)
            if btn:
                btn.click()
                page.wait_for_load_state("networkidle", timeout=20000)
                return True
        except Exception:
            continue
    # 1) 一覧のカード/リンク/タブ
    for sel in DETAIL_LINK_CANDIDATES_FALLBACK:
        try:
            el = page.query_selector(sel)
            if el:
                el.click()
                page.wait_for_load_state("networkidle", timeout=20000)
                return True
        except Exception:
            continue
    return False

def find_and_download_csv(page):
    # 三点メニューや More を先に開く（そこに CSV がある UI 対応）
    for more_sel in ["text=More", "[aria-label*='More']", "[aria-label*='Options']",
                     "button:has-text('...')", "[aria-haspopup='menu']"]:
        try:
            btn = page.query_selector(more_sel)
            if btn:
                btn.click()
                time.sleep(0.5)
        except Exception:
            pass

    # 1) 代表的な文言を総当たり
    for sel in CSV_BUTTON_CANDIDATES + ["text=Download", "text=Export"]:
        try:
            btn = page.query_selector(sel)
            if not btn:
                continue
            with page.expect_download(timeout=20000) as dl_info:
                btn.click()
            return dl_info.value
        except Exception:
            continue

    # 2) a / button の href / text に csv / download / export を含む要素を総当たり
    try:
        for a in page.query_selector_all("a, button"):
            try:
                href = (a.get_attribute("href") or "").lower()
                text = (a.inner_text() or "").lower()
                download_attr = a.get_attribute("download")
                if any(k in href for k in ["csv", "download", "export"]) or \
                   any(k in text for k in ["csv", "download", "export"]) or \
                   download_attr:
                    with page.expect_download(timeout=20000) as dl_info:
                        a.click()
                    return dl_info.value
            except Exception:
                continue
    except Exception:
        pass
    return None

def login_and_download(
    email: str,
    password: str,
    outdir: Path,
    sport: str,
    headless: bool,
    max_retries: int,
    debug_scan: bool = False,
) -> Optional[Path]:
    outdir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        ctx = browser.new_context(accept_downloads=True)
        page = ctx.new_page()

        # --- ログイン（直リンクで） ---
        page.goto(DK_LOGIN_URL, wait_until="domcontentloaded")
        email_inp = find_first(page, EMAIL_CANDIDATES, timeout_ms=20000)
        pass_inp  = find_first(page, PASS_CANDIDATES, timeout_ms=20000)
        if not email_inp or not pass_inp:
            raise RuntimeError("ログイン画面の入力欄が見つかりませんでした。UI変更の可能性。")
        email_inp.fill(email)
        pass_inp.fill(password)
        try:
            page.click(LOGIN_SUBMIT_SEL, timeout=3000)
        except Exception:
            pass_inp.press("Enter")

        maybe_handle_twofa(page)
        page.wait_for_load_state("networkidle", timeout=25000)
        time.sleep(1.0)

        # 念のためロビーへ
        page.goto(DK_LOBBY_URL, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=25000)

        # --- コンテスト詳細へ ---
        if not open_any_contest_detail(page):
            log("コンテスト詳細に入れませんでした。UIが変わっている可能性があります。")

        # --- 診断モード：候補列挙して終了 ---
        if debug_scan:
            log("=== クリック候補スキャン（csv/download/export を含む要素） ===")
            try:
                for a in page.query_selector_all("a, button"):
                    try:
                        href = a.get_attribute("href") or ""
                        text = (a.inner_text() or "").strip()
                        ltext = text.lower()
                        lhref = href.lower()
                        if any(s in ltext for s in ["csv", "download", "export"]) or \
                           any(s in lhref for s in ["csv", "download", "export"]):
                            print(f"TEXT: {text} | HREF: {href}")
                    except Exception:
                        continue
            except Exception:
                pass
            browser.close()
            return None

        # --- ダウンロードをリトライ ---
        last_err: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                log(f"Download CSV 試行 {attempt}/{max_retries} …")
                dl = find_and_download_csv(page)
                if not dl:
                    raise RuntimeError("ダウンロードリンクが見つかりませんでした。ページ構造の変更の可能性があります。")

                tmp_path = outdir / f"DKSalaries_tmp_{int(time.time())}.csv"
                try:
                    dl.save_as(tmp_path.as_posix())
                except Exception:
                    suggested = dl.suggested_filename or f"DKSalaries_{int(time.time())}.csv"
                    dl_path = outdir / suggested
                    dl.save_as(dl_path.as_posix())
                    tmp_path = dl_path

                if is_duplicate(tmp_file=tmp_path, outdir=outdir):
                    tmp_path.unlink(missing_ok=True)
                    log("同一内容のCSVのためスキップ（重複）")
                    browser.close()
                    return None

                ts = time.strftime('%Y%m%d_%H%M%S')
                final_path = outdir / f"{sport.upper()}_{ts}_DKSalaries.csv"
                tmp_path.rename(final_path)
                log(f"保存しました: {final_path}")
                browser.close()
                return final_path
            except Exception as e:
                last_err = e
                wait = min(2 ** attempt, 16)
                log(f"失敗: {e} → {wait}s待って再試行")
                time.sleep(wait)

        browser.close()
        if last_err:
            log(f"最終的に失敗: {last_err}")
        return None

# -------------------- CLI --------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='DraftKings テンプレ自動ダウンロード（最小サンプル）')
    p.add_argument('--sport', required=True, help='例: MLB / NBA / NFL など')
    p.add_argument('--outdir', required=True, help='保存先ディレクトリ')
    p.add_argument('--headful', action='store_true', help='ブラウザを表示（ヘッドフル）')
    p.add_argument('--max-retries', type=int, default=3, help='DLリトライ回数')
    p.add_argument('--debug-scan', action='store_true', help='スレート詳細でクリック候補（csv/download/export）を列挙して終了')
    return p.parse_args()

def main() -> int:
    load_dotenv()
    email = os.getenv('DK_EMAIL')
    password = os.getenv('DK_PASSWORD')
    if not email or not password:
        log('DK_EMAIL / DK_PASSWORD が .env にありません。')
        return 2

    args = parse_args()
    outdir = Path(args.outdir)
    saved = login_and_download(
        email=email,
        password=password,
        outdir=outdir,
        sport=args.sport,
        headless=(not args.headful),
        max_retries=args.max_retries,
        debug_scan=args.debug_scan,
    )
    return 0

if __name__ == '__main__':
    sys.exit(main())
def dump_clickables(page, label: str):
    log(f"=== {label}: clickable candidates on page ===")
    try:
        for el in page.query_selector_all("a, button"):
            try:
                txt = (el.inner_text() or "").strip().replace("\n", " ")[:120]
                href = el.get_attribute("href") or ""
                if txt or ("csv" in href.lower() or "contest" in href.lower() or "draft" in href.lower()):
                    print(f"TEXT: {txt} | HREF: {href}")
            except Exception:
                continue
    except Exception:
        pass
